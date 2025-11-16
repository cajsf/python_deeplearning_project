from fastapi import FastAPI, HTTPException, Depends, status, Query
from pydantic import BaseModel
import bcrypt 
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pymysql.err import Error as MySQLError
from queries import (
    create_user,
    get_user_by_username,
    get_user_allergies,
    search_foods_by_name,
    get_food_details_by_id,
    get_allergies_for_food,
    get_all_allergies,
    add_user_allergy_by_id,
    delete_user_allergy_by_id,
    delete_user
)

#JWT 설정
SECRET_KEY = "4b77851cf47fdb77d433a3793435ded83916ef7aec69f26f222cb5db6673acdb"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30# 토큰 만료 시간

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

app = FastAPI()

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

class FoodDetails(BaseModel):
    food_id: int
    food_name: str
    food_url: Optional[str] = None
    company_name: Optional[str] = None

class Allergy(BaseModel):
    allergy_id: int
    allergy_name: str

class FoodDetailsResponse(BaseModel):
    food: FoodDetails
    allergies: List[Allergy]
    warning: Optional[List[str]] = None

class UserAllergyCreate(BaseModel):
    allergy_id: int

class UserDelete(BaseModel):
    password: str

def create_access_token(data: dict):# JWT 토큰 생성
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):# 현재 사용자 정보 가져오기
    credentials_exception = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail ="유효하지 않은 인증입니다.",
        headers = {"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        
        user_id: int = payload.get("user_id")
        db_user = get_user_by_username(username)
        
        if db_user is None or db_user['user_id'] != user_id:
            raise credentials_exception
        
        return db_user
    
    except JWTError:
        raise credentials_exception

def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme_optional)):
    if token is None:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        
        user_id: int = payload.get("user_id")
        db_user = get_user_by_username(username)
        
        if db_user is None or db_user['user_id'] != user_id:
            return None
        
        return db_user

    except (JWTError, AttributeError):
        return None

@app.post("/api/auth/register")# 회원가입
def register_user(user: UserCreate):
    if get_user_by_username(user.username):
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다.")
    
    try:
        create_user(user.username, user.password)
        return {"message": "회원가입이 완료되었습니다.", "username": user.username}
    except  Exception as e:
        raise HTTPException(status_code=500, detail="회원가입 중 오류가 발생했습니다.")

@app.post("/api/auth/login", response_model=Token)# 로그인
def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    db_user = get_user_by_username(form_data.username)
    if not (db_user and bcrypt.checkpw(form_data.password.encode('utf-8'), db_user['password'].encode('utf-8'))):
        raise HTTPException(
            status_code=401,
            detail="아이디 또는 비밀번호가 일치하지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = {
        "sub": db_user['username'],
        "user_id": db_user['user_id'],
        "role": db_user['role']
    }
    
    access_token = create_access_token(data=token_data)
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/users/me")# 내 정보 및 알레르기 조회
def read_users_me(current_user:  dict = Depends(get_current_user)):
    user_id = current_user['user_id']
    
    my_allergies = get_user_allergies(user_id)
    
    user_info = {
        "user_id": current_user['user_id'],
        "username": current_user['username'],
        "role": current_user['role'],
    }
    
    return {"user": user_info, "allergies": my_allergies}

@app.get("/api/food/search", response_model=List[FoodSearchResult])
def search_food(q: str = Query(..., min_length = 1, description = "검색할 식품 이름")):
    results = search_foods_by_name(q)
    if not results:
        return []
    return results

@app.get("/api/food/{food_id}", response_model=FoodDetailsResponse)
def get_food_detail(
    food_id: int,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    food_details = get_food_details_by_id(food_id)
    if not food_details:
        raise HTTPException(status_code=404, detail="식품을 찾을 수 없습니다.")
    
    food_allergies = get_allergies_for_food(food_id)
    
    warning_list = None
    if current_user:
        print(f"로그인한 사용자({current_user['username']})의 개인화 경고를 확인합니다.")
        user_allergies = get_user_allergies(current_user['user_id'])
        
        user_allergy_names = {a['allergy_name'] for a in user_allergies}
        food_allergy_names = {a['allergy_name'] for a in food_allergies}
        
        common_allergies = user_allergy_names.intersection(food_allergy_names)
        
        if common_allergies:
            warning_list = list(common_allergies)
    
    response = {
        "food": food_details,
        "allergies": food_allergies,
        "warning": warning_list
    }
    return response

@app.get("/api/allergies", response_model=List[Allergy])
def get_all_allergy_list():
    allergies = get_all_allergies()
    return allergies

@app.post("/api/users/me/allergies", response_model=Allergy, status_code=status.HTTP_201_CREATED)
def add_my_allergy(
    allergy_data: UserAllergyCreate,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user['user_id']
    allergy_id = allergy_data.allergy_id
    
    try:
        new_allergy = add_user_allergy_by_id(user_id, allergy_id)
        
        if  new_allergy is None:
            raise HTTPException(status_code=400, detail="이미 등록됐거나 존재하지 않는 알레르기 유발 물질입니다.")
        return new_allergy
    
    except MySQLError as e:
        if e.args[0] == 1062:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 등록된 알레르기 유발 물질입니다."
            )
        elif e.args[0] == 1452:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="존재하지 않는 알레르기 유발 물질입니다."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"알레르기 유발 물질 등록 중 오류가 발생했습니다: {e}"
            )

@app.delete("/api/users/me/allergies/{allergy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_allergy(
    allergy_id: int,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user['user_id']
    
    success = delete_user_allergy_by_id(user_id, allergy_id)
    if not success:
        raise HTTPException(status_code=404, detail="등록되지 않은 알레르기 유발 물질입니다.")

    return {"detail": "알레르기 유발 물질이 성공적으로 삭제되었습니다."}

@app.delete("/api/users/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(
    delete_data: UserDelete,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user['user_id']
    
    if not bcrypt.checkpw(delete_data.password.encode('utf-8'), current_user['password'].encode('utf-8')):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비밀번호가 일치하지 않습니다."
        )
    
    success = delete_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="계정 삭제에 실패했습니다."
        )
    
    return {"detail": "계정이 성공적으로 삭제되었습니다."}


@app.get("/")
def read_root():
    return {"message": "파기딥 프로젝트 API 서버에 오신 것을 환영합니다."}