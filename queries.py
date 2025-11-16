import pymysql
from pymysql.err import MySQLError
import bcrypt

def connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='1234',
        database='Food_Allergy_DB',
        port=3306,
        cursorclass=pymysql.cursors.DictCursor
    )

def get_food_id(food_name):
    db = connection()
    try:
        with db.cursor() as cursor:
            sql = "SELECT food_id, food_name FROM Food WHERE food_name like %s limit 1"
            pattern = f"%{food_name}%"
            cursor.execute(sql, (pattern,))
            result = cursor.fetchone()
            if result:
                return result['food_id'], result['food_name']
            return None, None
    finally:
        db.close()


def get_allergies_for_food(food_id):
    db = connection()
    try:
        with db.cursor() as cursor:
            sql = """
                SELECT A.allergy_id, A.allergy_name
                FROM Allergy as A
                inner join Food_Allergy as FA ON A.allergy_id = FA.allergy_id
                WHERE fa.food_id = %s
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
                inner join Allergy_Alternative_Food AAF ON AF.alternative_food_id = AAF.alternative_food_id
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
                inner join Allergy_Cross_Reaction ACR ON CR.cross_reaction_id = ACR.cross_reaction_id
                WHERE ACR.allergy_id = %s
            """
            cursor.execute(sql, (allergy_id,))
            return cursor.fetchall()
    finally:
        db.close()

def insert_data(food_name, company_name):
    db = connection()
    try:
        with db.cursor() as cursor:
            sql = "SELECT company_id FROM Company WHERE company_name = %s"
            cursor.execute(sql, (company_name,))
            row = cursor.fetchone()
            company_id = row['company_id']
            sql = "INSERT INTO Food (company_id, food_name) VALUES (%s, %s)"
            cursor.execute(sql, (company_id, food_name))
            db.commit()
            print(f"'{food_name}' 제품이 '{company_name}' 회사에 추가되었습니다.")
    except MySQLError as e:
        print(f"데이터베이스 오류: {e}")
    finally:
        db.close()

def delete_data(food_name, company_name):
    db = connection()
    try:
        with db.cursor() as cursor:
            sql = "SELECT food_id FROM Food WHERE food_name = %s AND company_id = (SELECT company_id FROM Company WHERE company_name = %s)"
            cursor.execute(sql, (food_name, company_name))
            row = cursor.fetchone()
            if not row:
                print(f"'{food_name}' 제품이 '{company_name}' 회사에 존재하지 않습니다.")
                return
            food_id = row['food_id']
            sql = "DELETE FROM Food WHERE food_id = %s"
            cursor.execute(sql, (food_id,))
            
            sql = "DELETE FROM Food_Allergy where food_id = %s"
            cursor.execute(sql, (food_id,))
            db.commit()
            print(f"'{food_name}' 제품이 '{company_name}' 회사에서 삭제되었습니다.")
    except MySQLError as e:
        print(f"데이터베이스 오류: {e}")
    finally:
        db.close()

def insert_allergy_data(food_name, company_name, allergy_name):
    db = connection()
    try:
        with db.cursor() as cursor:
            sql = "SELECT food_id FROM Food WHERE food_name = %s AND company_id = (SELECT company_id FROM Company WHERE company_name = %s)"
            cursor.execute(sql, (food_name, company_name))
            row = cursor.fetchone()
            if not row:
                print(f"'{food_name}' 제품이 '{company_name}' 회사에 존재하지 않습니다.")
                return
            food_id = row['food_id']
            
            sql = "SELECT allergy_id FROM Allergy WHERE allergy_name = %s"
            cursor.execute(sql, (allergy_name,))
            row = cursor.fetchone()
            if not row:
                print(f"'{allergy_name}'은(는) 알레르기 유발물질 표시대상이 아닙니다.")
                return
            allergy_id = row['allergy_id']
            
            sql = "INSERT INTO Food_Allergy (food_id, allergy_id) VALUES (%s, %s)"
            cursor.execute(sql, (food_id, allergy_id))
            db.commit()
            print(f"'{food_name}' 제품에 '{allergy_name}' 알레르기 정보가 추가되었습니다.")
    except MySQLError as e:
        print(f"데이터베이스 오류: {e}")
    finally:
        db.close()

def update_allergy_data():
    db = connection()
    try:
        with db.cursor() as cursor:
            food_name = input("수정할 제품명을 입력하세요: ").strip()
            if not food_name:
                print("제품명은 필수 입력입니다.")
                return
            company_name = input("회사를 입력하세요: ").strip()
            if not company_name:
                print("회사명은 필수 입력입니다.")
                return
            sql = "SELECT food_id FROM Food WHERE food_name = %s AND company_id = (SELECT company_id FROM Company WHERE company_name = %s)"
            cursor.execute(sql, (food_name, company_name))
            row = cursor.fetchone()
            if not row:
                print(f"'{food_name}' 제품이 '{company_name}' 회사에 존재하지 않습니다.")
                return
            food_id = row['food_id']
            
            print(f"=='{food_name}'의 식품 알레르기 유발 물질 정보==")
            sql = "SELECT A.allergy_id, A.allergy_name FROM Allergy as A INNER JOIN Food_Allergy as FA ON A.allergy_id = FA.allergy_id WHERE FA.food_id = %s"
            cursor.execute(sql, (food_id,))
            allergies = cursor.fetchall()
            if not allergies:
                print(f"'{food_name}' 제품에는 등록된 알레르기 유발 성분이 없습니다.")
                return
            for a in allergies:
                print(f"- 성분: {a['allergy_name']}")
            
            allergy_list = input(f"수정할 알레르기 유발 성분명을 쉼표로 구분하여 입력하세요: ").split(',')
            allergy_list = [name.strip() for name in allergy_list]
            if not allergy_list:
                print("알레르기 유발 성분명을 하나 이상 입력해야 합니다.")
                return

            sql = "DELETE FROM Food_Allergy WHERE food_id = %s"
            cursor.execute(sql, (food_id,))
            
            for allergy_name in allergy_list:
                sql_find = "SELECT allergy_id FROM Allergy WHERE allergy_name = %s"
                cursor.execute(sql_find, (allergy_name,))
                result = cursor.fetchone()
                if not result:
                    print(f"'{allergy_name}'은(는) 알레르기 유발물질 표시대상이 아닙니다. 건너뜁니다.")
                    continue
                allergy_id = result['allergy_id']
                
                sql_insert = "INSERT INTO Food_Allergy (food_id, allergy_id) VALUES (%s, %s)"
                cursor.execute(sql_insert, (food_id, allergy_id))
            
            db.commit()
            print(f"\n'{food_name}' 제품의 알레르기 정보가 성공적으로 수정되었습니다.")
    except MySQLError as e:
        print(f"데이터베이스 오류: {e}")
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
            print(f"'{username}' 계정이 성공적으로 생성되었습니다.")
    except MySQLError as e:
        if e.args[0] == 1062:
            print(f"오류: '{username}'은(는) 이미 사용 중인 아이디입니다.")
        else:
            print(f"사용자 생성 오류: {e}")
    finally:
        db.close()

def get_user_by_username(username):
    db = connection()
    try:
        with db.cursor() as cursor:
            sql = "SELECT * FROM Users WHERE username = %s"
            cursor.execute(sql, (username,))
            return cursor.fetchone()
    finally:
        db.close()

def add_user_allergy(user_id, allergy_name):
    db = connection()
    try:
        with db.cursor() as cursor:
            sql_find_allergy = "SELECT allergy_id FROM Allergy WHERE allergy_name = %s"
            cursor.execute(sql_find_allergy, (allergy_name,))
            result = cursor.fetchone()
            
            if not result:
                print(f"'{allergy_name}'은(는) 등록된 알레르기 정보가 아닙니다.")
                return
            
            allergy_id = result['allergy_id']
            
            sql_insert = "INSERT INTO User_Allergies (user_id, allergy_id) VALUES (%s, %s)"
            cursor.execute(sql_insert, (user_id, allergy_id))
            db.commit()
            print(f"내 알레르기 정보에 '{allergy_name}'이(가) 추가되었습니다.")
    except MySQLError as e:
        if e.args[0] == 1062:
            print(f"이미 등록된 알레르기 정보입니다.")
        else:
            print(f"알레르기 정보 추가 오류: {e}")
    finally:
        db.close()

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

def delete_user(user_id):
    db = connection()
    try:
        with db.cursor() as cursor:
            sql_check_role = "SELECT role FROM Users WHERE user_id = %s"
            cursor.execute(sql_check_role, (user_id,))
            user_data = cursor.fetchone()
            
            if user_data and user_data['role'] == 'admin':
                print("\n시스템 오류: 관리자 계정은 삭제할 수 없습니다.")
                return False
            
            sql = "DELETE FROM Users WHERE user_id = %s"
            cursor.execute(sql, (user_id,))
            db.commit()
            return True
        
    except MySQLError as e:
        print(f"\n회원 삭제 오류: {e}")
        return False
    finally:
        db.close()

def get_all_users():
    db = connection()
    try:
        with db.cursor() as cursor:
            sql = "SELECT username, role FROM Users"
            cursor.execute(sql)
            return cursor.fetchall()
    finally:
        db.close()

def get_top_allergies(limit = 5):
    db = connection()
    try:
        with db.cursor() as cursor:
            sql = """
                SELECT A.allergy_name, COUNT(UA.user_id) as 'registration_count'
                FROM User_Allergies as UA
                inner JOIN Allergy as A ON UA.allergy_id = A.allergy_id
                GROUP BY A.allergy_name
                ORDER BY registration_count DESC
                LIMIT %s
            """
            cursor.execute(sql, (limit,))
            return cursor.fetchall()
    finally:
        db.close()

def search_foods_by_name(food_name):
    db = connection()
    try:
        with db.cursor() as cursor:
            sql = "SELECT food_id, food_name, food_url FROM food where food_name LIKE %s"
            pattern = f"%{food_name}%"
            cursor.execute(sql, (pattern,))
            results =  cursor.fetchall()
            return results
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
            result = cursor.fetchone()
            return result
    finally:
        db.close()

def get_all_allergies():
    db = connection()
    try:
        with db.cursor() as cursor:
            sql = "SELECT allergy_id, allergy_name FROM Allergy ORDER BY allergy_name"
            cursor.execute(sql)
            return cursor.fetchall()
    finally:
        db.close()

def add_user_allergy_by_id(user_id, allergy_id):
    db = connection()
    try:
        with db.cursor() as cursor:
            sql = "INSERT INTO user_allergies(user_id, allergy_id)  values(%s, %s)"
            cursor.execute(sql, (user_id, allergy_id))
            db.commit()
            
            sql_check = """
                SELECT A.allergy_id, A.allergy_name
                FROM Allergy as A
                WHERE A.allergy_id = %s
            """
            cursor.execute(sql_check, (allergy_id,))
            return cursor.fetchone()
    except MySQLError as e:
        db.rollback()
        print(f"add_user_allergy_by_id 오류: {e}")
        raise e
    finally:
        db.close()

def delete_user_allergy_by_id(user_id, allergy_id):
    db = connection()
    try:
        with db.cursor() as cursor:
            sql = "DELETE FROM user_allergies WHERE user_id = %s AND allergy_id = %s"
            affected_rows = cursor.execute(sql, (user_id, allergy_id))
            db.commit()
            return affected_rows > 0
    
    except MySQLError as e:
        db.rollback()
        print(f"delete_user_allergy_by_id 오류: {e}")
        return False
    
    finally:
        db.close()