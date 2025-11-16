import time
import bcrypt
from queries import (
    get_food_id,
    get_allergies_for_food,
    get_alternatives_for_allergy,
    get_cross_reactions_for_allergy,
    insert_data,
    delete_data,
    insert_allergy_data,
    update_allergy_data,
    create_user,
    get_user_by_username,
    add_user_allergy,
    get_user_allergies,
    delete_user,
    get_all_users,
    get_top_allergies
)

current_user = None

def print_func():
    print("\n" + "="*15 + " 식품 알레르기 확인 프로그램 " + "="*15)
    
    if current_user:
        print(f"({current_user['username']} 님, 환영합니다!)\n")
    else:
        print("(로그인되지 않았습니다)\n")

    print("--- 식품 정보 ---")
    print("(1) 식품 알레르기 조회")
    print("(2) 제품 정보 추가")
    print("(3) 식품 알레르기 정보 추가")
    print("(4) 식품 알레르기 정보 수정")
    print("(5) 제품 정보 삭제")

    print("\n--- 사용자 메뉴 ---")
    if not current_user:
        print("(6) 회원가입")
        print("(7) 로그인")
    elif current_user['role'] == 'user':
        print("(6) 내 알레르기 정보 관리")
        print("(7) 로그아웃")
        print("(8) 회원 탈퇴")
    elif current_user['role'] == 'admin':
        print("(6) 관리자 메뉴")
        print("(7) 로그아웃")

    print("\n(0) 프로그램 종료")
    print("-" * 50)

def search_food_func():
    """식품 정보를 조회하고, 로그인 시 개인화 알림을 제공하는 함수"""
    print("\n=== (1) 식품 알레르기 유발물질 확인 ===")
    while True:
        food_name = input("조회할 제품명을 입력하세요 (종료하려면 엔터): ").strip()
        if not food_name:
            print("\n식품 알레르기 조회를 종료합니다.")
            break
        
        company_name = input("조회할 회사명을 입력하세요: ").strip()
        
        food_id, db_food_name = get_food_id(food_name)
        if not food_id:
            print(f"‘{food_name}’에 대한 정보가 없습니다.\n")
            continue
        
        print(f"\n'{db_food_name}'의 알레르기 유발 성분을 조회합니다...")
        time.sleep(0.5)

        allergies = get_allergies_for_food(food_id)
        if not allergies:
            print(f"‘{db_food_name}’에는 등록된 알레르기 유발 성분이 없습니다.")
        else:
            for a in allergies:
                aid, aname = a['allergy_id'], a['allergy_name']
                print(f"\n- 성분: {aname}")

                alts = get_alternatives_for_allergy(aid)
                print("  대체 식품: ", ", ".join(alts) if alts else "정보 없음")

                crosses = get_cross_reactions_for_allergy(aid)
                if crosses:
                    print("  교차반응군:")
                    for cr in crosses:
                        print(f"    • {cr['cross_reaction_name']} (반응률: {cr['cross_reactivity_rate']}%)")
                else:
                    print("  교차반응군: 정보 없음")
        
        if current_user:
            print("\n--- [개인 맞춤 알림] ---")
            user_allergies_result = get_user_allergies(current_user['user_id'])
            user_allergy_ids = [ua['allergy_id'] for ua in user_allergies_result] if user_allergies_result else []
            
            if allergies:
                food_allergy_ids = [a['allergy_id'] for a in allergies]
                matched_allergies = [a for a in allergies if a['allergy_id'] in user_allergy_ids]

                if matched_allergies:
                    for match in matched_allergies:
                        print(f"주의! '{current_user['username']}'님께서 등록하신 '{match['allergy_name']}' 성분이 포함되어 있습니다!")
                else:
                    print(f"'{current_user['username']}'님의 알레르기와 일치하는 성분이 없습니다.")
            else:
                print("이 식품에는 알레르기 정보가 없어 안전합니다.")
        
        print("\n" + "="*30 + "\n")

# --- 기존 데이터 관리 함수들 ---
def insert_func():
    print("\n=== (2) 제품 정보 추가 ===")
    food_name = input("추가할 제품명을 입력하세요: ").strip()
    if not food_name:
        print("제품명은 필수 입력입니다.")
        return
    
    company_name = input("회사를 입력하세요: ").strip()
    if not company_name:
        print("회사명은 필수 입력입니다.")
        return
    
    insert_data(food_name, company_name)

def insert_allergy_func():
    print("\n=== (3) 식품 알레르기 정보 추가 ===")
    food_name = input("알레르기 정보를 추가할 제품명을 입력하세요: ").strip()
    if not food_name:
        print("제품명은 필수 입력입니다.")
        return
    
    company_name = input("회사를 입력하세요: ").strip()
    if not company_name:
        print("회사명은 필수 입력입니다.")
        return
    
    allergy_name = input("추가할 알레르기 유발 성분명을 입력하세요: ").strip()
    if not allergy_name:
        print("알레르기 유발 성분명은 필수 입력입니다.")
        return
    
    insert_allergy_data(food_name, company_name, allergy_name)

def update_allergy_func():
    print("\n=== (4) 알레르기 정보 수정 ===")
    update_allergy_data()

def delete_func():
    print("\n=== (5) 제품 정보 삭제 ===")
    food_name = input("삭제할 제품명을 입력하세요: ").strip()
    if not food_name:
        print("제품명은 필수 입력입니다.")
        return
    
    company_name = input("회사를 입력하세요: ").strip()
    if not company_name:
        print("회사명은 필수 입력입니다.")
        return
    
    delete_data(food_name, company_name)

def register_func():
    print("\n=== (6) 회원가입 ===")
    username = input("사용할 아이디: ").strip()
    password = input("사용할 비밀번호: ").strip()
    
    re_password = input("비밀번호 확인: ").strip()
    
    if password != re_password:
        print("\n오류: 비밀번호가 다릅니다.")
        return
    
    if len(password) < 8:
        print("\n오류: 비밀번호는 8자리 이상이어야 합니다.")
        return
    
    if username and password:
        create_user(username, password)
    else:
        print("아이디와 비밀번호는 필수입니다.")

def login_func():
    global current_user
    print("\n=== (7) 로그인 ===")
    username = input("아이디: ").strip()
    password = input("비밀번호: ").strip()
    
    user_data = get_user_by_username(username)
    if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data['password'].encode('utf-8')):
        current_user = user_data
        print(f"\n'{current_user['username']}'님, 환영합니다!")
    else:
        print("\n아이디 또는 비밀번호가 일치하지 않습니다.")

def my_allergy_func():
    while True:
        print("\n=== (6) 내 알레르기 정보 관리 ===")
        my_allergies = get_user_allergies(current_user['user_id'])
        if my_allergies:
            print("현재 등록된 내 알레르기:", ", ".join([a['allergy_name'] for a in my_allergies]))
        else:
            print("등록된 알레르기 정보가 없습니다.")
        
        print("\n(1) 알레르기 추가 (2) 메뉴로 돌아가기")
        choice = input("선택: ").strip()
        
        if choice == '1':
            allergy_name = input("추가할 알레르기명을 입력하세요: ").strip()
            if allergy_name:
                add_user_allergy(current_user['user_id'], allergy_name)
        elif choice == '2':
            break
        else:
            print("잘못된 입력입니다.")

def logout_func():
    global current_user
    if current_user:
        print(f"\n'{current_user['username']}'님이 로그아웃하셨습니다.")
        current_user = None
    else:
        print("로그인 상태가 아닙니다.")

def delete_account_func():
    """회원 탈퇴 처리 함수"""
    global current_user
    
    print("\n=== (8) 회원 탈퇴 ===")
    confirm = input(f"'{current_user['username']}' 계정을 정말 삭제하시겠습니까? 되돌릴 수 없습니다. (y/n): ").lower()
    
    if confirm == 'y':
        password = input("비밀번호를 입력하여 본인인증을 완료하세요: ").strip()
        
        password_from_db = current_user['password'].encode('utf-8')
        password_to_check = password.encode('utf-8')

        if bcrypt.checkpw(password_to_check, password_from_db):
            if delete_user(current_user['user_id']):
                print("\n회원 탈퇴가 성공적으로 처리되었습니다. 이용해주셔서 감사합니다.")
                current_user = None
            else:
                print("\n회원 탈퇴 처리 중 오류가 발생했습니다.")
        else:
            print("\n비밀번호가 일치하지 않습니다. 탈퇴가 취소되었습니다.")
    else:
        print("\n회원 탈퇴가 취소되었습니다.")

def admin_menu_func():
    while True:
        print("\n=== 관리자 메뉴 ===")
        print("(1) 전체 사용자 목록 보기")
        print("(2) 최다 등록 알레르기 TOP 5")
        print("(3) 메인 메뉴로 돌아가기")
        
        choice = input("선택: ").strip()
        
        if choice == '1':
            users = get_all_users()
            print("\n--- 전체 사용자 목록 ---")
            for user in users:
                print(f"유저 아이디: {user['username']}, 역할: {user['role']}")
        
        elif choice == '2':
            top_allergies = get_top_allergies()
            print("\n--- 최다 등록 알레르기 TOP 5 ---")
            for i, allergy in enumerate(top_allergies, 1):
                print(f"{i}위: {allergy['allergy_name']} ({allergy['registration_count']}명)")
        
        elif choice == '3':
            break
        else:
            print("잘못된 입력입니다.")


if __name__ == "__main__":
    while True:
        print_func()
        try:
            menu = int(input("선택하세요 ==> "))
        except ValueError:
            print("숫자를 입력해주세요.")
            continue

        if menu == 1:
            search_food_func()
        elif menu == 2:
            insert_func()
        elif menu == 3:
            insert_allergy_func()
        elif menu == 4:
            update_allergy_func()
        elif menu == 5:
            delete_func()
        elif menu == 6 and not current_user:#로그인 안했을 때
            register_func()
        elif menu == 7 and not current_user:
            login_func()

        elif menu == 6 and current_user['role'] == 'user':#로그인 했을 때
            my_allergy_func()
        elif menu == 7 and current_user['role'] == 'user':
            logout_func()
        elif menu == 8 and current_user['role'] == 'user':
            delete_account_func()
        
        elif menu == 6 and current_user['role'] == 'admin':
            admin_menu_func()
        elif menu == 7 and current_user['role'] == 'admin':
            logout_func()
        
        elif menu == 0:
            print("\n프로그램을 종료합니다. 이용해주셔서 감사합니다.")
            break
        else:
            print("\n잘못된 메뉴 선택입니다. 다시 입력해주세요.")