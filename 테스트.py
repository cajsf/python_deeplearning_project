import os
import glob


BASE_TRAIN_LABEL = r"E:\데이터셋\건강관리를 위한 음식 이미지\Training\라벨"


print(f"1. 경로 확인 중: {BASE_TRAIN_LABEL}")
if not os.path.exists(BASE_TRAIN_LABEL):
    print("해당 경로가 존재하지 않습니다! 경로를 다시 확인해주세요.")
    exit()
else:
    print("경로가 존재합니다.")

print("\n2. 클래스 목록 만드는 중...")
classes = set()
search_path = os.path.join(BASE_TRAIN_LABEL, "*", "*")
found_folders = glob.glob(search_path)
for path in found_folders:
    if os.path.isdir(path):
        classes.add(os.path.basename(path))

print(f"찾은 클래스 개수: {len(classes)}개")
if len(classes) > 0:
    print(f"예시: {list(classes)[:5]}")
else:
    print("클래스(음식 폴더)를 하나도 못 찾았습니다. 폴더 구조가 예상과 다릅니다.")
    exit()

print("\n3. 실제 파일 탐색 테스트 (딱 10개만 확인해봅니다)...")
count = 0
found_json = False

for root, dirs, files in os.walk(BASE_TRAIN_LABEL):
    # JSON 파일이 있는지 확인
    json_files = [f for f in files if f.endswith('.json')]
    
    if not json_files:
        # JSON이 없는 폴더는 그냥 지나감 (너무 많으면 출력 생략)
        continue
        
    found_json = True
    current_folder_name = os.path.basename(root)
    print(f"\n 탐색 중인 폴더: {current_folder_name}")
    print(f"   - 경로: {root}")
    print(f"   - JSON 파일 개수: {len(json_files)}개")

    if current_folder_name in classes:
        print("   [OK] 이 폴더는 클래스 목록에 있습니다.")
        # 파일 하나만 열어보기 테스트
        try:
            test_file = os.path.join(root, json_files[0])
            with open(test_file, 'r', encoding='utf-8') as f:
                print("   [OK] 파일 읽기 성공")
        except Exception as e:
            print(f"   [Error] 파일 읽기 실패: {e}")
    else:
        print(f"   [Skip] '{current_folder_name}'은(는) 클래스 목록에 없습니다.")

    count += 1
    if count >= 5:
        print("\n진단 종료")
        break

if not found_json:
    print("\n전체를 훑었지만 JSON 파일을 하나도 못 찾았습니다. 폴더 깊이가 너무 깊거나 경로가 잘못되었습니다.")