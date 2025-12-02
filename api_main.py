from fastapi import FastAPI, HTTPException, Depends, status, Query, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import bcrypt 
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pymysql.err import Error as MySQLError
import os
import shutil
from PIL import Image 
import io
import json

# [추가됨] AI 관련 라이브러리
from ultralytics import YOLO
import google.generativeai as genai 

from queries import (
    create_user,
    get_user_by_username,
    get_user_allergies,
    search_foods_advanced,
    get_food_details_by_id,
    get_allergies_for_food,
    get_all_allergies,
    add_user_allergy_by_id,
    delete_user_allergy_by_id,
    delete_user,
    create_food_with_allergies,
    get_alternatives_for_allergy,
    get_cross_reactions_for_allergy,
    get_all_users,
    get_top_allergies,
    update_user_profile,
    update_user_password,
    get_recent_foods,
    delete_food_by_id,
    update_food_allergies
)

# --- [설정 영역] ---

# 1. JWT 설정
SECRET_KEY = "4b77851cf47fdb77d433a3793435ded83916ef7aec69f26f222cb5db6673acdb"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 2. Gemini API 키
GOOGLE_API_KEY = "AIzaSyAepLyPnrcHzsHNAkigCTK7eWStquAXGYY" 
try:
    genai.configure(api_key=GOOGLE_API_KEY)
except:
    print("Gemini API 설정 실패 (키 누락 등)")

# 3. YOLO 모델 로드
MODEL_PATH = "C:\\Users\\rkdal\\Desktop\\학교\\3-2\\파이썬기반딥러닝\\기말 프로젝트\\Food_Detection_Project\\train_result_300sample\\weights\\best.pt"
local_model = None
try:
    if os.path.exists(MODEL_PATH):
        print("🔄 YOLO 모델 로딩 중...")
        local_model = YOLO(MODEL_PATH)
        print("✅ YOLO 모델 로드 완료!")
    else:
        print(f"⚠️ 모델 파일을 찾을 수 없습니다: {MODEL_PATH}")
except Exception as e:
    print(f"❌ 모델 로드 에러: {e}")


# [MLOps] 데이터 수집용 폴더 생성
if not os.path.exists("static/ai_temp"): os.makedirs("static/ai_temp")       # 임시 저장소
if not os.path.exists("static/dataset/images"): os.makedirs("static/dataset/images") # 피드백 받은 이미지 (학습용)
if not os.path.exists("static/dataset/labels"): os.makedirs("static/dataset/labels") # 정답 라벨 (학습용)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if not os.path.exists(os.path.join(BASE_DIR, "static/profiles")):
    os.makedirs(os.path.join(BASE_DIR, "static/profiles"))

STATIC_DIR = os.path.join(BASE_DIR, "static")

# 3. [중요] 터미널에 경로를 출력해서 확인해봅시다.
print("\n" + "="*50)
print(f"✅ 현재 main.py 위치: {BASE_DIR}")
print(f"✅ 파이썬이 찾은 static 폴더: {STATIC_DIR}")

if os.path.exists(STATIC_DIR):
    print("🎉 폴더가 실제로 존재합니다! 연결을 시도합니다.")
else:
    print("🚨 [오류] 폴더가 없습니다! 경로를 다시 확인해주세요.")
print("="*50 + "\n")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models (기존 유지) ---
class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class UserCreate(BaseModel):
    username: str
    password: str
    nickname: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class FoodSearchResult(BaseModel):
    food_id: int
    food_name: str
    food_url: Optional[str] = None
    food_img_url: Optional[str] = None
    allergy_ids: List[int] = []

class FoodDetails(BaseModel):
    food_id: int
    food_name: str
    food_url: Optional[str] = None
    food_img_url: Optional[str] = None
    company_name: Optional[str] = None

class Allergy(BaseModel):
    allergy_id: int
    allergy_name: str

class CrossReaction(BaseModel):
    cross_reaction_name: str
    cross_reactivity_rate: Optional[int] = None

class FoodDetailsResponse(BaseModel):
    food: FoodDetails
    allergies: List[Allergy]
    warning: Optional[List[str]] = None
    alternatives: Optional[List[str]] = []
    cross_reactions: Optional[List[CrossReaction]] = []

class UserAllergyCreate(BaseModel):
    allergy_id: int

class UserDelete(BaseModel):
    password: str

class FoodCreate(BaseModel):
    food_name: str
    company_name: str
    food_url: Optional[str] = None
    allergy_ids: List[int] = []

class FoodUpdateAllergy(BaseModel):
    allergy_ids: List[int]

class UserInfo(BaseModel):
    user_id: int
    username: str
    role: str

class AllergyStat(BaseModel):
    allergy_name: str
    registration_count: int

class FeedbackCreate(BaseModel):
    filename: str
    correct_name: str

# --- Utils ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail ="유효하지 않은 인증입니다.",
        headers = {"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: raise credentials_exception
        user_id: int = payload.get("user_id")
        db_user = get_user_by_username(username)
        if db_user is None or db_user['user_id'] != user_id: raise credentials_exception
        return db_user
    except JWTError: raise credentials_exception

def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme_optional)):
    if token is None: return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: return None
        user_id: int = payload.get("user_id")
        db_user = get_user_by_username(username)
        if db_user is None or db_user['user_id'] != user_id: return None
        return db_user
    except (JWTError, AttributeError): return None

def get_current_admin_user(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="관리자 권한이 필요합니다.")
    return current_user

# --- Routes ---

# [핵심] AI 이미지 분석 API (로컬 YOLO + Gemini 하이브리드)
# api_main.py 의 predict_food 함수 교체

@app.post("/api/ai/predict")
async def predict_food(file: UploadFile = File(...)):
    # 1. 이미지 읽기
    image_data = await file.read()
    image = Image.open(io.BytesIO(image_data))
    
    # [MLOps 1] 분석 요청된 이미지를 임시 폴더에 저장 (파일명: 날짜_시간.jpg)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    temp_filename = f"{timestamp}.jpg"
    temp_path = f"static/ai_temp/{temp_filename}"
    
    # RGB 변환 후 저장 (YOLO 학습용은 보통 JPG 사용)
    if image.mode in ("RGBA", "P"): image = image.convert("RGB")
    image.save(temp_path, quality=90)
    
    detected_name = None
    confidence = 0.0
    source = "None"
    ingredients = []

    print("\n" + "="*50)
    print(f"📸 이미지 분석 시작: {file.filename}")

    # ---------------------------------------------------------
    # [Step 1] 로컬 YOLO 모델 예측
    # ---------------------------------------------------------
    if local_model:
        try:
            results = local_model.predict(image, conf=0.1, verbose=False) 
            for r in results:
                for box in r.boxes:
                    current_conf = float(box.conf[0])
                    if current_conf > confidence:
                        confidence = current_conf
                        cls_id = int(box.cls[0])
                        detected_name = r.names[cls_id]
            
            if detected_name:
                print(f"🤖 로컬 모델 탐지: '{detected_name}' ({confidence*100:.2f}%)")
            else:
                print("🤖 로컬 모델: 탐지된 객체 없음")
        except Exception as e:
            print(f"❌ 로컬 모델 에러: {e}")

    # ---------------------------------------------------------
    # [Step 2] Gemini 호출 (정확도 70% 미만일 때)
    # ---------------------------------------------------------
    if detected_name is None or confidence < 0.7: 
        print(f"⚠️ 정확도 부족 ({confidence*100:.2f}%). Gemini 호출 시도...")
        
        if GOOGLE_API_KEY == "여기에_GEMINI_API_KEY_입력":
            if detected_name: source = f"Local AI (Low Conf: {confidence*100:.0f}%)"
        else:
            try:
                gemini_model = genai.GenerativeModel('gemini-2.5-flash')
                prompt = """
                이 음식 사진을 분석해줘. 한국인이 주로 먹는 음식 이름으로 알려줘.
                예: '김치찌개', '라면', '갈비탕' 처럼 보편적인 이름으로.
                다음 JSON 형식으로만 답변해 (다른 말 금지):
                {"food_name": "음식 이름", "ingredients": ["주재료1", "주재료2"]}
                """
                response = gemini_model.generate_content([prompt, image])
                text = response.text.replace("```json", "").replace("```", "").strip()
                ai_data = json.loads(text)
                
                detected_name = ai_data.get("food_name")
                ingredients = ai_data.get("ingredients", [])
                source = "Gemini Cloud AI"
                print(f"✨ Gemini 분석 성공: '{detected_name}'")
            except Exception as e:
                print(f"❌ Gemini 에러: {e}")
                if detected_name: source = f"Local AI (Low Conf: {confidence*100:.0f}%)"
    else:
        print(f"✅ 로컬 모델 확신! ({confidence*100:.2f}%)")
        source = f"Local AI (YOLO) - {confidence*100:.0f}%"
    
    print("="*50 + "\n")

    # ---------------------------------------------------------
    # [Step 3] 결과 반환 (DB 매칭 제거됨)
    # ---------------------------------------------------------
    
    if not detected_name:
        return {"name": "분석 실패", "ingredients": [], "source": "Failed"}

    # 로컬 모델은 재료 정보를 안 주므로, 비어있으면 기본 메시지
    if not ingredients:
        ingredients = ["상세 재료 정보는 Gemini 또는 상세 검색을 확인하세요"]

    # DB에서 억지로 매칭해서 이름을 바꾸는 코드를 삭제했습니다.
    # AI가 찾은 이름 그대로 돌려줍니다. -> 프론트엔드에서 이 이름으로 검색을 수행합니다.
    return {
        "name": detected_name,
        "ingredients": ingredients, # (기존 변수 그대로)
        "source": source,           # (기존 변수 그대로)
        "filename": temp_filename   # [추가됨] 프론트엔드가 피드백 줄 때 쓸 파일명
    }

# --- (아래는 기존 코드 그대로 유지) ---
@app.get("/api/auth/check-username")
def check_username_availability(username: str = Query(..., min_length=1)):
    # 이미 있는 아이디인지 확인
    if get_user_by_username(username):
        return {"available": False, "message": "이미 사용 중인 아이디입니다."}
    else:
        return {"available": True, "message": "사용 가능한 아이디입니다."}

@app.post("/api/auth/register")
def register_user(user: UserCreate):
    if get_user_by_username(user.username):
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다.")
    try:
        # 닉네임도 같이 전달
        create_user(user.username, user.password, user.nickname)
        return {"message": "가입 완료"}
    except Exception as e:
        print(f"회원가입 에러: {e}")
        raise HTTPException(status_code=500, detail="회원가입 중 오류가 발생했습니다.")

@app.post("/api/auth/login", response_model=Token)
def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    db_user = get_user_by_username(form_data.username)
    if not (db_user and bcrypt.checkpw(form_data.password.encode('utf-8'), db_user['password'].encode('utf-8'))):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 일치하지 않습니다.", headers={"WWW-Authenticate": "Bearer"})
    
    token_data = {"sub": db_user['username'], "user_id": db_user['user_id'], "role": db_user['role']}
    access_token = create_access_token(data=token_data)
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/users/me")
def read_users_me(current_user: dict = Depends(get_current_user)):
    user_id = current_user['user_id']
    my_allergies = get_user_allergies(user_id)
    
    user_info = {
        "user_id": current_user['user_id'],
        "username": current_user['username'],
        "role": current_user['role'],
        "nickname": current_user.get('nickname'),
        "profile_image": current_user.get('profile_image')
    }
    return {"user": user_info, "allergies": my_allergies}

@app.post("/api/users/me/allergies", status_code=status.HTTP_201_CREATED)
def add_my_allergy(allergy_data: UserAllergyCreate, current_user: dict = Depends(get_current_user)):
    try:
        new_allergy = add_user_allergy_by_id(current_user['user_id'], allergy_data.allergy_id)
        if new_allergy is None: raise HTTPException(status_code=400, detail="존재하지 않는 알레르기입니다.")
        return new_allergy
    except MySQLError as e:
        if e.args[0] == 1062: raise HTTPException(status_code=409, detail="이미 등록된 알레르기입니다.")
        raise HTTPException(status_code=500, detail="알레르기 등록 실패")

@app.delete("/api/users/me/allergies/{allergy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_allergy(allergy_id: int, current_user: dict = Depends(get_current_user)):
    if not delete_user_allergy_by_id(current_user['user_id'], allergy_id):
        raise HTTPException(status_code=404, detail="등록되지 않은 알레르기입니다.")
    return {"detail": "삭제됨"}

@app.delete("/api/users/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(delete_data: UserDelete, current_user: dict = Depends(get_current_user)):
    if not bcrypt.checkpw(delete_data.password.encode('utf-8'), current_user['password'].encode('utf-8')):
        raise HTTPException(status_code=401, detail="비밀번호 불일치")
    if not delete_user(current_user['user_id']):
        raise HTTPException(status_code=403, detail="계정 삭제 실패")
    return {"detail": "삭제됨"}

# [수정된 안전한 검색 함수]
@app.get("/api/food/search", response_model=List[FoodSearchResult])
def search_food(
    q: str = Query(..., min_length=1, description="검색할 식품 이름"),
    page: int = Query(1, ge=1, description="페이지 번호 (기본 1)"),
    limit: int = Query(10, ge=1, le=100, description="한 페이지당 개수 (기본 10)"),
    avoid: Optional[List[int]] = Query(None, description="제외할 알레르기 ID 목록")
):
    offset = (page - 1) * limit
    
    try:
        results = search_foods_advanced(q, avoid, limit, offset)
    except Exception as e:
        print(f"DB 검색 오류: {e}")
        return [] 
    
    if not results:
        return []
    
    for row in results:
        raw_ids = row.get('allergy_ids')

        if not raw_ids:
            row['allergy_ids'] = []
            continue

        if isinstance(raw_ids, bytes):
            raw_ids = raw_ids.decode('utf-8')

        if isinstance(raw_ids, str):
            try:
                row['allergy_ids'] = [int(x.strip()) for x in raw_ids.split(',') if x.strip().isdigit()]
            except ValueError:
                print(f"데이터 변환 경고: {raw_ids}")
                row['allergy_ids'] = [] 
        elif isinstance(raw_ids, int):
            row['allergy_ids'] = [raw_ids]
        elif isinstance(raw_ids, list):
            row['allergy_ids'] = raw_ids
        else:
            row['allergy_ids'] = []
            
    return results

@app.get("/api/food/{food_id}", response_model=FoodDetailsResponse)
def get_food_detail(food_id: int, current_user: Optional[dict] = Depends(get_current_user_optional)):
    food_details = get_food_details_by_id(food_id)
    if not food_details: raise HTTPException(status_code=404, detail="식품을 찾을 수 없습니다.")
    
    food_allergies = get_allergies_for_food(food_id)
    
    # 1. 경고 분석 (내 알레르기와 겹치는지)
    warning_list = None
    if current_user:
        u_al = {a['allergy_name'] for a in get_user_allergies(current_user['user_id'])}
        f_al = {a['allergy_name'] for a in food_allergies}
        common = u_al.intersection(f_al)
        if common: warning_list = list(common)

    # 2. 교차 반응 분석 (의학적 정보 제공)
    cross_reactions_list = []
    seen_crs = set()
    for allergy in food_allergies:
        crs = get_cross_reactions_for_allergy(allergy['allergy_id'])
        for cr in crs:
            if cr['cross_reaction_name'] not in seen_crs:
                cross_reactions_list.append(cr)
                seen_crs.add(cr['cross_reaction_name'])

    # [수정] alternatives(대체식품), related_foods(관련제품) 모두 제거
    return {
        "food": food_details,
        "allergies": food_allergies,
        "warning": warning_list,
        "alternatives": [], # 빈 리스트 반환 (에러 방지용)
        "cross_reactions": cross_reactions_list
    }

@app.get("/api/allergies", response_model=List[Allergy])
def get_all_allergy_list():
    return get_all_allergies()

@app.post("/api/admin/food", status_code=status.HTTP_201_CREATED)
def create_new_food(food_data: FoodCreate, current_user: dict = Depends(get_current_admin_user)):
    try:
        food_id = create_food_with_allergies(food_data.food_name, food_data.company_name, food_data.food_url, food_data.allergy_ids)
        if not food_id: raise HTTPException(status_code=404, detail="회사를 찾을 수 없습니다.")
        return {"message": "제품 등록 성공", "food_id": food_id}
    except MySQLError as e:
        raise HTTPException(status_code=500, detail=f"DB 오류: {e}")

@app.put("/api/admin/food/{food_id}/allergies")
def update_food_allergy_info(food_id: int, update_data: FoodUpdateAllergy, current_user: dict = Depends(get_current_admin_user)):
    try:
        success = update_food_allergies(food_id, update_data.allergy_ids)
        if not success: raise HTTPException(status_code=404, detail="식품을 찾을 수 없습니다.")
        return {"message": "알레르기 정보 수정 성공"}
    except MySQLError as e:
        raise HTTPException(status_code=500, detail=f"DB 오류: {e}")

@app.delete("/api/admin/food/{food_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_food_item(food_id: int, current_user: dict = Depends(get_current_admin_user)):
    if not delete_food_by_id(food_id):
        raise HTTPException(status_code=404, detail="삭제 실패: 식품이 없거나 DB 오류")
    return {"detail": "삭제됨"}

@app.get("/api/admin/users", response_model=List[UserInfo])
def read_all_users(current_user: dict = Depends(get_current_admin_user)):
    return get_all_users()

@app.get("/api/admin/stats", response_model=List[AllergyStat])
def read_allergy_stats(limit: int = 5, current_user: dict = Depends(get_current_admin_user)):
    return get_top_allergies(limit)

@app.put("/api/users/me/profile")
async def update_profile(
    nickname: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user['user_id']
    image_path = None

    if file:
        filename = f"user_{user_id}.webp"
        file_location = f"static/profiles/{filename}"
        try:
            image = Image.open(file.file)
            image.thumbnail((400, 400))
            image.save(file_location, format="WEBP", quality=80, optimize=True)
            image_path = f"/static/profiles/{filename}"
        except Exception as e:
            print(f"이미지 저장 오류: {e}")
            raise HTTPException(status_code=500, detail="이미지 처리 실패")

    success = update_user_profile(user_id, nickname, image_path)
    if not success:
        raise HTTPException(status_code=500, detail="프로필 수정 실패")
    
    return {
        "message": "프로필이 업데이트되었습니다.", 
        "profile_image": image_path, 
        "nickname": nickname
    }

@app.put("/api/users/me/password")
def change_password(
    pw_data: PasswordChange,
    current_user: dict = Depends(get_current_user)
):
    if not bcrypt.checkpw(pw_data.current_password.encode('utf-8'), current_user['password'].encode('utf-8')):
        raise HTTPException(status_code=400, detail="현재 비밀번호가 일치하지 않습니다.")
    
    success = update_user_password(current_user['user_id'], pw_data.new_password)
    if not success:
        raise HTTPException(status_code=500, detail="비밀번호 변경 실패")
        
    return {"message": "비밀번호가 변경되었습니다."}

@app.get("/api/admin/foods")
def read_recent_foods(
    q: Optional[str] = Query(None), # 검색어 받기 (없으면 None)
    current_user: dict = Depends(get_current_admin_user)
):
    # 검색어(q)를 queries.py 함수로 전달
    return get_recent_foods(query=q)

@app.get("/")
def read_root():
    return {"message": "파기딥 프로젝트 API 서버 (Full Version)"}

# [MLOps] 사용자 피드백 저장 API
@app.post("/api/ai/feedback")
def save_feedback(data: FeedbackCreate):
    temp_path = f"static/ai_temp/{data.filename}"
    target_path = f"static/dataset/images/{data.filename}"
    
    # 1. 임시 폴더에 있던 이미지를 '학습 데이터 폴더'로 이동
    if os.path.exists(temp_path):
        shutil.move(temp_path, target_path)
    else:
        # 이미 이동했거나 없으면 패스 (혹은 에러 처리)
        if not os.path.exists(target_path):
            return {"message": "이미지가 만료되었습니다."}

    # 2. 정답 라벨 저장 (CSV 형태: 파일명, 정답)
    # 나중에 이 파일을 읽어서 모델 재학습에 사용함
    log_file = "static/dataset/labels/feedback_log.csv"
    
    # 파일이 없으면 헤더 작성
    if not os.path.exists(log_file):
        with open(log_file, "w", encoding="utf-8-sig") as f:
            f.write("filename,correct_label,timestamp\n")
            
    # 내용 추가 (Append 모드)
    with open(log_file, "a", encoding="utf-8-sig") as f:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{data.filename},{data.correct_name},{now}\n")
        
    print(f"📈 [MLOps] 사용자 피드백 수집됨: {data.correct_name}")
    return {"message": "소중한 데이터 감사합니다! 모델 학습에 반영됩니다."}

# api_main.py 의 analyze_ingredients 함수 교체

# [수정됨] 관리자 성분표 스캔 (Gemini 1.5 Flash 활용 - 가장 빠르고 정확)
@app.post("/api/admin/ocr")
async def analyze_ingredients(file: UploadFile = File(...)):
    # 1. 이미지 읽기
    image_data = await file.read()
    image = Image.open(io.BytesIO(image_data))

    print(f"📸 관리자 OCR 요청 (Gemini): {file.filename}")
    
    # 2. DB에 있는 모든 알레르기 이름 가져오기 (매칭용)
    all_allergy_list = get_all_allergies()
    allergy_names_str = ", ".join([a['allergy_name'] for a in all_allergy_list])

    detected_allergies = [] 
    raw_text = ""

    try:
        # 3. Gemini 1.5 Flash에게 OCR + 분석 시키기
        if GOOGLE_API_KEY == "여기에_GEMINI_API_KEY_입력":
            return {"error": "API 키가 설정되지 않았습니다."}

        gemini_model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
        이 이미지는 식품 뒷면의 '원재료명' 부분이야.
        1. 이미지에 보이는 글자를 모두 읽어줘.
        2. 읽은 내용 중에 다음 알레르기 유발 물질 목록에 해당하는 단어가 있다면 찾아줘.
        [목록: {allergy_names_str}]
        
        반드시 아래 JSON 형식으로만 대답해 (다른 말 금지):
        {{
            "raw_text": "이미지에서 읽은 텍스트 요약",
            "found_allergies": ["우유", "대두", "밀"] 
        }}
        """
        
        response = gemini_model.generate_content([prompt, image])
        text = response.text.replace("```json", "").replace("```", "").strip()
        ai_data = json.loads(text)
        
        raw_text = ai_data.get("raw_text", "")
        found_names = ai_data.get("found_allergies", [])
        
        print(f"✨ OCR 분석 성공: {found_names}")

        # 4. 찾은 이름을 DB의 ID로 변환 (체크박스 체크용)
        for found in found_names:
            for db_item in all_allergy_list:
                # 포함 관계 확인 (예: '대두'가 '탈지대두'에 포함됨)
                if db_item['allergy_name'] in found or found in db_item['allergy_name']:
                    if db_item['allergy_id'] not in detected_allergies:
                        detected_allergies.append(db_item['allergy_id'])

    except Exception as e:
        print(f"❌ OCR 에러: {e}")
        # 에러가 나도 죽지 않고 빈 결과 반환 (그래야 프론트가 안 멈춤)
        return {"raw_text": "분석 실패", "detected_ids": []}

    return {
        "raw_text": raw_text,
        "detected_ids": detected_allergies
    }