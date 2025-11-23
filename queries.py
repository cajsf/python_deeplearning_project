import pymysql
from pymysql.err import MySQLError
import bcrypt

# ==========================================
# [1] 공통 유틸리티
# ==========================================
def connection():
    return pymysql.connect(
        host='127.0.0.1',  # [중요] 'localhost' 대신 '127.0.0.1' 사용! (속도 해결)
        user='root',
        password='1234',
        database='Food_Allergy_DB',
        port=3306,
        cursorclass=pymysql.cursors.DictCursor
    )

# ==========================================
# [2] 사용자 및 인증 관련
# ==========================================
def get_user_by_username(username):
    db = connection()
    try:
        with db.cursor() as cursor:
            sql = "SELECT * FROM Users WHERE username = %s"
            cursor.execute(sql, (username,))
            return cursor.fetchone()
    finally:
        db.close()

def create_user(username, plain_password):
    db = connection()
    try:
        with db.cursor() as cursor:
            password_bytes = plain_password.encode('utf-8')
            hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
            sql = "INSERT INTO Users (username, password) VALUES (%s, %s)"
            cursor.execute(sql, (username, hashed_password.decode('utf-8')))
            db.commit()
    except MySQLError as e:
        raise e
    finally:
        db.close()

def delete_user(user_id):
    db = connection()
    try:
        with db.cursor() as cursor:
            sql_check = "SELECT role FROM Users WHERE user_id = %s"
            cursor.execute(sql_check, (user_id,))
            user_data = cursor.fetchone()
            if user_data and user_data['role'] == 'admin':
                return False 
            
            cursor.execute("DELETE FROM Users WHERE user_id = %s", (user_id,))
            db.commit()
            return True
    except MySQLError:
        return False
    finally:
        db.close()

# ==========================================
# [3] 사용자 알레르기 관리
# ==========================================
def get_user_allergies(user_id):
    db = connection()
    try:
        with db.cursor() as cursor:
            sql = """
                SELECT A.allergy_id, A.allergy_name 
                FROM User_Allergies as UA
                JOIN Allergy as A ON UA.allergy_id = A.allergy_id
                WHERE UA.user_id = %s
            """
            cursor.execute(sql, (user_id,))
            return cursor.fetchall()
    finally:
        db.close()

def add_user_allergy_by_id(user_id, allergy_id):
    db = connection()
    try:
        with db.cursor() as cursor:
            # 알레르기 존재 확인
            cursor.execute("SELECT allergy_id, allergy_name FROM Allergy WHERE allergy_id = %s", (allergy_id,))
            allergy = cursor.fetchone()
            if not allergy: return None 

            cursor.execute("INSERT INTO user_allergies(user_id, allergy_id) values(%s, %s)", (user_id, allergy_id))
            db.commit()
            return allergy
    except MySQLError as e:
        raise e
    finally:
        db.close()

def delete_user_allergy_by_id(user_id, allergy_id):
    db = connection()
    try:
        with db.cursor() as cursor:
            rows = cursor.execute("DELETE FROM user_allergies WHERE user_id = %s AND allergy_id = %s", (user_id, allergy_id))
            db.commit()
            return rows > 0
    except MySQLError:
        return False
    finally:
        db.close()

# ==========================================
# [4] 식품 조회 및 검색 (심화 정보 포함)
# ==========================================

# queries.py 내부 수정

def search_foods_advanced(food_name, avoid_allergy_ids=None, limit=10, offset=0):
    db = connection()
    try:
        with db.cursor() as cursor:
            # [수정] GROUP_CONCAT을 사용하여 해당 식품의 알레르기 ID들을 '1,2,3' 형태의 문자열로 함께 가져옴
            sql = """
                SELECT F.food_id, F.food_name, F.food_url, 
                GROUP_CONCAT(FA.allergy_id) as allergy_ids
                FROM Food F
                LEFT JOIN Food_Allergy FA ON F.food_id = FA.food_id
                WHERE F.food_name LIKE %s
            """
            params = [f"%{food_name}%"]

            # 안심 필터링 (SQL 레벨에서 제외)
            if avoid_allergy_ids:
                format_strings = ','.join(['%s'] * len(avoid_allergy_ids))
                sql += f"""
                    AND F.food_id NOT IN (
                        SELECT food_id FROM Food_Allergy 
                        WHERE allergy_id IN ({format_strings})
                    )
                """
                params.extend(avoid_allergy_ids)

            # 그룹핑 및 페이징
            sql += " GROUP BY F.food_id LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            cursor.execute(sql, tuple(params))
            return cursor.fetchall()
    finally:
        db.close()

def get_food_details_by_id(food_id):
    db = connection()
    try:
        with db.cursor() as cursor:
            sql = """
                SELECT F.food_id, F.food_name, F.food_url, C.company_name
                From Food as F
                LEFT JOIN Company as C on F.company_id = C.company_id
                WHERE F.food_id = %s
            """
            cursor.execute(sql, (food_id,))
            return cursor.fetchone()
    finally:
        db.close()

def get_allergies_for_food(food_id):
    db = connection()
    try:
        with db.cursor() as cursor:
            sql = """
                SELECT A.allergy_id, A.allergy_name
                FROM Allergy as A
                JOIN Food_Allergy as FA ON A.allergy_id = FA.allergy_id
                WHERE FA.food_id = %s
            """
            cursor.execute(sql, (food_id,))
            return cursor.fetchall()
    finally:
        db.close()

def get_alternatives_for_allergy(allergy_id):
    db = connection()
    try:
        with db.cursor() as cursor:
            sql = """
                SELECT AF.alternative_food_name
                FROM Alternative_Food AF
                JOIN Allergy_Alternative_Food AAF ON AF.alternative_food_id = AAF.alternative_food_id
                WHERE AAF.allergy_id = %s
            """
            cursor.execute(sql, (allergy_id,))
            rows = cursor.fetchall()
            return [row['alternative_food_name'] for row in rows]
    finally:
        db.close()

def get_cross_reactions_for_allergy(allergy_id):
    db = connection()
    try:
        with db.cursor() as cursor:
            sql = """
                SELECT CR.cross_reaction_name, ACR.cross_reactivity_rate
                FROM Cross_Reaction CR
                JOIN Allergy_Cross_Reaction ACR ON CR.cross_reaction_id = ACR.cross_reaction_id
                WHERE ACR.allergy_id = %s
            """
            cursor.execute(sql, (allergy_id,))
            return cursor.fetchall()
    finally:
        db.close()

def get_all_allergies():
    db = connection()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT allergy_id, allergy_name FROM Allergy ORDER BY allergy_name")
            return cursor.fetchall()
    finally:
        db.close()

# ==========================================
# [5] 관리자 기능 (데이터 추가/수정/삭제/통계)
# ==========================================

# 1. 제품 및 알레르기 동시 등록
def create_food_with_allergies(food_name, company_name, food_url, allergy_ids):
    db = connection()
    try:
        with db.cursor() as cursor:
            # 회사 ID 확인
            cursor.execute("SELECT company_id FROM Company WHERE company_name = %s", (company_name,))
            company = cursor.fetchone()
            if not company: return None
            company_id = company['company_id']

            # 식품 등록
            cursor.execute("INSERT INTO Food (company_id, food_name, food_url) VALUES (%s, %s, %s)", 
                           (company_id, food_name, food_url))
            food_id = cursor.lastrowid

            # 알레르기 매핑
            if allergy_ids:
                sql_map = "INSERT INTO Food_Allergy (food_id, allergy_id) VALUES (%s, %s)"
                for aid in allergy_ids:
                    cursor.execute(sql_map, (food_id, aid))
            
            db.commit()
            return food_id
    except MySQLError as e:
        db.rollback()
        raise e
    finally:
        db.close()

# 2. 제품의 알레르기 정보 수정 (기존 정보 삭제 후 재등록)
def update_food_allergies(food_id, new_allergy_ids):
    db = connection()
    try:
        with db.cursor() as cursor:
            # 식품 존재 확인
            cursor.execute("SELECT food_id FROM Food WHERE food_id = %s", (food_id,))
            if not cursor.fetchone(): return False

            # 기존 알레르기 삭제
            cursor.execute("DELETE FROM Food_Allergy WHERE food_id = %s", (food_id,))

            # 새 알레르기 등록
            if new_allergy_ids:
                sql_map = "INSERT INTO Food_Allergy (food_id, allergy_id) VALUES (%s, %s)"
                for aid in new_allergy_ids:
                    cursor.execute(sql_map, (food_id, aid))
            
            db.commit()
            return True
    except MySQLError as e:
        db.rollback()
        raise e
    finally:
        db.close()

# 3. 제품 삭제
def delete_food_by_id(food_id):
    db = connection()
    try:
        with db.cursor() as cursor:
            # Food_Allergy 테이블은 CASCADE 설정이 되어 있다고 가정하거나, 명시적으로 삭제
            cursor.execute("DELETE FROM Food_Allergy WHERE food_id = %s", (food_id,))
            cursor.execute("DELETE FROM Food WHERE food_id = %s", (food_id,))
            db.commit()
            return True # 삭제 성공
    except MySQLError:
        db.rollback()
        return False
    finally:
        db.close()

# 4. 전체 회원 조회
def get_all_users():
    db = connection()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT user_id, username, role FROM Users")
            return cursor.fetchall()
    finally:
        db.close()

# 5. 알레르기 통계
def get_top_allergies(limit=5):
    db = connection()
    try:
        with db.cursor() as cursor:
            sql = """
                SELECT A.allergy_name, COUNT(UA.user_id) as registration_count
                FROM User_Allergies as UA
                JOIN Allergy as A ON UA.allergy_id = A.allergy_id
                GROUP BY A.allergy_name, A.allergy_id
                ORDER BY registration_count DESC
                LIMIT %s
            """
            cursor.execute(sql, (int(limit),))
            return cursor.fetchall()
    finally:
        db.close()


def update_user_profile(user_id, nickname=None, profile_image=None):
    db = connection()
    try:
        with db.cursor() as cursor:
            # 변경할 값이 있는 경우에만 쿼리 생성
            updates = []
            params = []
            
            if nickname is not None:
                updates.append("nickname = %s")
                params.append(nickname)
            
            if profile_image is not None:
                updates.append("profile_image = %s")
                params.append(profile_image)
            
            if not updates:
                return False # 변경할 내용 없음

            sql = f"UPDATE Users SET {', '.join(updates)} WHERE user_id = %s"
            params.append(user_id)
            
            cursor.execute(sql, tuple(params))
            db.commit()
            return True
    except MySQLError:
        return False
    finally:
        db.close()

def update_user_password(user_id, new_password):
    db = connection()
    try:
        with db.cursor() as cursor:
            password_bytes = new_password.encode('utf-8')
            hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
            
            sql = "UPDATE Users SET password = %s WHERE user_id = %s"
            cursor.execute(sql, (hashed_password.decode('utf-8'), user_id))
            db.commit()
            return True
    except MySQLError:
        return False
    finally:
        db.close()

def get_recent_foods(limit=100):
    db = connection()
    try:
        with db.cursor() as cursor:
            sql = """
                SELECT F.food_id, F.food_name, C.company_name 
                FROM Food F 
                LEFT JOIN Company C ON F.company_id = C.company_id
                ORDER BY F.food_id DESC 
                LIMIT %s
            """
            cursor.execute(sql, (limit,))
            return cursor.fetchall()
    finally:
        db.close()