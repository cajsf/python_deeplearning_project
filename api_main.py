from fastapi import FastAPI, HTTPException, Depends, status, Query
from pydantic import BaseModel
from typing import List, Optional
from fastapi.staticfiles import StaticFiles
from fastapi import File, UploadFile, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt
from pymysql.err import Error as MySQLError
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from PIL import Image
import io

# queries.py에서 모든 함수 가져오기
from queries import (
    create_user,
    get_user_by_username,
    delete_user,
    get_user_allergies,
    add_user_allergy_by_id,
    delete_user_allergy_by_id,
    search_foods_advanced,
    get_food_details_by_id,
    get_allergies_for_food,
    get_all_allergies,
    get_alternatives_for_allergy, #심화정보
    get_cross_reactions_for_allergy, # 심화 정보
    create_food_with_allergies, # 관리자 데이터 관리
    update_food_allergies, # 관리자 데이터 관리
    delete_food_by_id, # 관리자 데이터 관리
    get_all_users, # 통계 및 회원관리
    get_top_allergies, # 통계 및 회원관리
    update_user_profile,
    update_user_password,
    get_recent_foods
)

# JWT 설정
SECRET_KEY = "4b77851cf47fdb77d433a3793435ded83916ef7aec69f26f222cb5db6673acdb"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # 모든 주소에서 접근 허용 (보안상 실무에선 제한하지만, 지금은 개발용이라 OK)
    allow_credentials=True,
    allow_methods=["*"],      # 모든 HTTP 메소드(GET, POST 등) 허용
    allow_headers=["*"],      # 모든 헤더 허용
)

if not os.path.exists("static/profiles"):
    os.makedirs("static/profiles")

app.mount("/static", StaticFiles(directory="static"), name="static")

# --- [Pydantic Models] ---

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class UserCreate(BaseModel):
    username: str
    password: str

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
    allergy_ids: List[int] = []

class FoodDetails(BaseModel):
    food_id: int
    food_name: str
    food_url: Optional[str] = None
    company_name: Optional[str] = None

class Allergy(BaseModel):
    allergy_id: int
    allergy_name: str

# 심화 정보를 위한 모델
class CrossReaction(BaseModel):
    cross_reaction_name: str
    cross_reactivity_rate: Optional[int] = None

class FoodDetailsResponse(BaseModel):
    food: FoodDetails
    allergies: List[Allergy]
    warning: Optional[List[str]] = None
    alternatives: Optional[List[str]] = [] # 대체 식품 리스트
    cross_reactions: Optional[List[CrossReaction]] = [] # 교차 반응 정보

class UserAllergyCreate(BaseModel):
    allergy_id: int

class UserDelete(BaseModel):
    password: str

# 관리자용 모델
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

# --- [인증 관련 함수] ---

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="유효하지 않은 인증입니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: raise credentials_exception
        
        user_id: int = payload.get("user_id")
        db_user = get_user_by_username(username)
        
        if db_user is None or db_user['user_id'] != user_id:
            raise credentials_exception
        return db_user
    except JWTError:
        raise credentials_exception

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
    except (JWTError, AttributeError):
        return None

def get_current_admin_user(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="관리자 권한이 필요합니다.")
    return current_user

# --- [API 라우터] ---

@app.post("/api/auth/register")
def register_user(user: UserCreate):
    if get_user_by_username(user.username):
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다.")
    try:
        create_user(user.username, user.password)
        return {"message": "회원가입이 완료되었습니다.", "username": user.username}
    except Exception:
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
    
    # [수정됨] DB에 있는 닉네임과 프로필 이미지도 같이 보내줍니다!
    user_info = {
        "user_id": current_user['user_id'],
        "username": current_user['username'],
        "role": current_user['role'],
        "nickname": current_user.get('nickname'),          # 추가됨
        "profile_image": current_user.get('profile_image') # 추가됨
    }
    
    return {"user": user_info, "allergies": my_allergies}

@app.post("/api/users/me/allergies", status_code=status.HTTP_201_CREATED)
def add_my_allergy(allergy_data: UserAllergyCreate, current_user: dict = Depends(get_current_user)):
    try:
        new_allergy = add_user_allergy_by_id(current_user['user_id'], allergy_data.allergy_id)
        if new_allergy is None:
            raise HTTPException(status_code=400, detail="존재하지 않는 알레르기입니다.")
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

@app.get("/api/food/search", response_model=List[FoodSearchResult])
def search_food(
    q: str = Query(..., min_length=1, description="검색할 식품 이름"),
    page: int = Query(1, ge=1, description="페이지 번호 (기본 1)"),
    limit: int = Query(10, ge=1, le=100, description="한 페이지당 개수 (기본 10)"),
    avoid: Optional[List[int]] = Query(None, description="제외할 알레르기 ID 목록")
):
    offset = (page - 1) * limit
    
    # 1. DB 검색 실행
    try:
        results = search_foods_advanced(q, avoid, limit, offset)
    except Exception as e:
        print(f"DB 검색 오류: {e}")
        return [] # DB 에러 시 빈 결과 반환
    
    if not results:
        return []
    
    # 2. 데이터 변환 (에러 방지 로직 적용)
    for row in results:
        # allergy_ids 컬럼 값을 가져옴 (없으면 None)
        raw_ids = row.get('allergy_ids')

        # 값이 없으면 빈 리스트 처리
        if not raw_ids:
            row['allergy_ids'] = []
            continue

        # [중요] 가끔 DB에서 bytes 타입(b'1,2,3')으로 줄 때가 있음 -> 문자열로 변환
        if isinstance(raw_ids, bytes):
            raw_ids = raw_ids.decode('utf-8')

        # 문자열("1,2,3")이면 콤마로 쪼개서 숫자 리스트로 변환
        if isinstance(raw_ids, str):
            try:
                # 공백 제거(strip)하고, 숫자인 것만(isdigit) 골라서 변환
                # 이렇게 해야 "1, 2, " 같이 끝에 쉼표가 있어도 에러가 안 남
                row['allergy_ids'] = [int(x.strip()) for x in raw_ids.split(',') if x.strip().isdigit()]
            except ValueError:
                print(f"데이터 변환 경고: {raw_ids}")
                row['allergy_ids'] = [] 
        
        # 이미 리스트나 정수라면 그대로 사용
        elif isinstance(raw_ids, int):
            row['allergy_ids'] = [raw_ids]
        elif isinstance(raw_ids, list):
            row['allergy_ids'] = raw_ids
        else:
            row['allergy_ids'] = []
            
    return results

# [중요] 심화 정보(대체식품, 교차반응) 포함된 상세 조회
@app.get("/api/food/{food_id}", response_model=FoodDetailsResponse)
def get_food_detail(food_id: int, current_user: Optional[dict] = Depends(get_current_user_optional)):
    # 1. 식품 기본 정보
    food_details = get_food_details_by_id(food_id)
    if not food_details: raise HTTPException(status_code=404, detail="식품을 찾을 수 없습니다.")
    
    # 2. 식품 알레르기 정보
    food_allergies = get_allergies_for_food(food_id)
    
    # 3. 사용자 맞춤 경고
    warning_list = None
    if current_user:
        user_allergies = get_user_allergies(current_user['user_id'])
        user_allergy_names = {a['allergy_name'] for a in user_allergies}
        food_allergy_names = {a['allergy_name'] for a in food_allergies}
        common = user_allergy_names.intersection(food_allergy_names)
        if common: warning_list = list(common)

    # 4. 대체 식품 및 교차 반응 조회
    alternatives_set = set()
    cross_reactions_list = []
    seen_crs = set()

    for allergy in food_allergies:
        aid = allergy['allergy_id']
        # 대체 식품
        alts = get_alternatives_for_allergy(aid)
        alternatives_set.update(alts)
        # 교차 반응
        crs = get_cross_reactions_for_allergy(aid)
        for cr in crs:
            # 중복 제거 (이름 기준)
            if cr['cross_reaction_name'] not in seen_crs:
                cross_reactions_list.append(cr)
                seen_crs.add(cr['cross_reaction_name'])

    return {
        "food": food_details,
        "allergies": food_allergies,
        "warning": warning_list,
        "alternatives": list(alternatives_set),
        "cross_reactions": cross_reactions_list
    }

@app.get("/api/allergies", response_model=List[Allergy])
def get_all_allergy_list():
    return get_all_allergies()

# --- [관리자 전용 API] ---

# 1. 제품 등록 (알레르기 포함)
@app.post("/api/admin/food", status_code=status.HTTP_201_CREATED)
def create_new_food(food_data: FoodCreate, current_user: dict = Depends(get_current_admin_user)):
    try:
        food_id = create_food_with_allergies(food_data.food_name, food_data.company_name, food_data.food_url, food_data.allergy_ids)
        if not food_id: raise HTTPException(status_code=404, detail="회사를 찾을 수 없습니다.")
        return {"message": "제품 등록 성공", "food_id": food_id}
    except MySQLError as e:
        raise HTTPException(status_code=500, detail=f"DB 오류: {e}")

# 2. 제품의 알레르기 정보 수정
@app.put("/api/admin/food/{food_id}/allergies")
def update_food_allergy_info(food_id: int, update_data: FoodUpdateAllergy, current_user: dict = Depends(get_current_admin_user)):
    try:
        success = update_food_allergies(food_id, update_data.allergy_ids)
        if not success: raise HTTPException(status_code=404, detail="식품을 찾을 수 없습니다.")
        return {"message": "알레르기 정보 수정 성공"}
    except MySQLError as e:
        raise HTTPException(status_code=500, detail=f"DB 오류: {e}")

# 3. 제품 삭제
@app.delete("/api/admin/food/{food_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_food_item(food_id: int, current_user: dict = Depends(get_current_admin_user)):
    if not delete_food_by_id(food_id):
        raise HTTPException(status_code=404, detail="삭제 실패: 식품이 없거나 DB 오류")
    return {"detail": "삭제됨"}

# 4. 전체 회원 조회
@app.get("/api/admin/users", response_model=List[UserInfo])
def read_all_users(current_user: dict = Depends(get_current_admin_user)):
    return get_all_users()

# 5. 통계 조회
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
        # [변경] 무조건 확장자를 .webp로 고정
        filename = f"user_{user_id}.webp"
        file_location = f"static/profiles/{filename}"
        
        try:
            # Pillow로 이미지 열기
            image = Image.open(file.file)
            
            # 투명 배경(PNG) 호환을 위해 RGBA 모드 유지 혹은 배경색 처리
            # WebP는 투명도(Alpha channel)를 지원하므로 'RGB'로 변환 안 해도 됨 (단, 호환성 위해 RGBA 유지)
            
            # 1. 썸네일 리사이징 (400x400) - 여전히 필요함 (4K 사진을 줄여야 하니까)
            image.thumbnail((400, 400))
            
            # 2. [핵심] WebP 포맷으로 저장
            # optimize=True: 용량 추가 최적화
            # quality=80: 사람 눈으로 구분 힘든 선에서 용량 대폭 감소
            image.save(file_location, format="WEBP", quality=80, optimize=True)
            
            # DB에는 webp 경로 저장
            image_path = f"/static/profiles/{filename}"
            
        except Exception as e:
            print(f"이미지 저장 오류: {e}")
            raise HTTPException(status_code=500, detail="이미지 처리 실패")

    # DB 업데이트
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
    # 현재 비밀번호 확인
    if not bcrypt.checkpw(pw_data.current_password.encode('utf-8'), current_user['password'].encode('utf-8')):
        raise HTTPException(status_code=400, detail="현재 비밀번호가 일치하지 않습니다.")
    
    # 비밀번호 변경
    success = update_user_password(current_user['user_id'], pw_data.new_password)
    if not success:
        raise HTTPException(status_code=500, detail="비밀번호 변경 실패")
        
    return {"message": "비밀번호가 변경되었습니다."}

@app.get("/api/admin/foods")
def read_recent_foods(current_user: dict = Depends(get_current_admin_user)):
    return get_recent_foods()

@app.get("/")
def read_root():
    return {"message": "파기딥 프로젝트 API 서버 (Full Version)"}