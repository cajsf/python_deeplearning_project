import os
import json
import shutil
import random
from tqdm import tqdm

# ==========================================
# 1. 설정 (개수 제한 추가됨!)
# ==========================================
# 음식별로 최대 몇 장 뽑을까요? (100~200 추천)
MAX_IMAGES_PER_CLASS = 300 

BASE_TRAIN_LABEL = r"E:\데이터셋\건강관리를 위한 음식 이미지\Training\라벨"
BASE_TRAIN_IMAGE = r"E:\데이터셋\건강관리를 위한 음식 이미지\Training\원천"
BASE_VAL_LABEL = r"E:\데이터셋\건강관리를 위한 음식 이미지\Validation\라벨"
BASE_VAL_IMAGE = r"E:\데이터셋\건강관리를 위한 음식 이미지\Validation\원천"

OUTPUT_DIR = r"E:\YOLO\datasets"

# ==========================================
# 2. 이미지 폴더 지도 생성
# ==========================================
def build_image_folder_map(image_root):
    print(f"이미지 폴더 위치를 파악 중입니다... ({image_root})")
    folder_map = {}
    for root, dirs, files in os.walk(image_root):
        folder_name = os.path.basename(root)
        has_image = False
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                has_image = True
                break
        if has_image:
            folder_map[folder_name] = root
    print(f"👉 총 {len(folder_map)}개의 이미지 폴더를 찾았습니다.")
    return folder_map

# ==========================================
# 3. 데이터 변환 실행 함수 (랜덤 샘플링 적용)
# ==========================================
def process_dataset(label_root, image_folder_map, output_root, split_name, class_to_id):
    img_dest = os.path.join(output_root, split_name, 'images')
    lbl_dest = os.path.join(output_root, split_name, 'labels')
    os.makedirs(img_dest, exist_ok=True)
    os.makedirs(lbl_dest, exist_ok=True)

    print(f"\n[{split_name}] 데이터 매칭 및 변환 시작 (클래스당 최대 {MAX_IMAGES_PER_CLASS}장 제한)...")
    
    total_processed = 0
    
    # os.walk로 모든 라벨 폴더를 돕니다.
    for root, dirs, files in os.walk(label_root):
        json_files = [f for f in files if f.endswith('.json')]
        if not json_files:
            continue

        # 라벨 폴더 이름 정제 ("가리비 json" -> "가리비")
        label_folder_name = os.path.basename(root)
        clean_name = label_folder_name.replace(" json", "").replace("_json", "").strip()
        
        # 이미지 폴더 찾기
        target_image_dir = image_folder_map.get(clean_name)
        if not target_image_dir:
            target_image_dir = image_folder_map.get(label_folder_name)
        
        if not target_image_dir or clean_name not in class_to_id:
            continue
            
        class_id = class_to_id[clean_name]

        # ==================================================
        # [핵심] 너무 많으면 랜덤으로 섞어서 N개만 뽑기!
        # ==================================================
        if len(json_files) > MAX_IMAGES_PER_CLASS:
            selected_files = random.sample(json_files, MAX_IMAGES_PER_CLASS)
        else:
            selected_files = json_files
            
        print(f"  Processing: {clean_name} ({len(selected_files)}장)")

        for filename in selected_files:
            try:
                # JSON 읽기
                json_path = os.path.join(root, filename)
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list): data = data[0]

                # 이미지 찾기
                image_filename = os.path.splitext(filename)[0] + ".jpg"
                src_image_path = os.path.join(target_image_dir, image_filename)
                
                # 확장자 체크
                if not os.path.exists(src_image_path):
                    if os.path.exists(src_image_path.replace(".jpg", ".JPG")):
                        src_image_path = src_image_path.replace(".jpg", ".JPG")
                    elif os.path.exists(src_image_path.replace(".jpg", ".jpeg")):
                        src_image_path = src_image_path.replace(".jpg", ".jpeg")
                    else:
                        continue 

                # YOLO 좌표 변환
                w = float(data['W'])
                h = float(data['H'])
                points = data['Point(x,y)'].split(',')
                x_center = float(points[0])
                y_center = float(points[1])
                
                yolo_line = f"{class_id} {x_center} {y_center} {w} {h}\n"
                
                # 복사 및 저장
                shutil.copy2(src_image_path, os.path.join(img_dest, image_filename))
                
                txt_filename = os.path.splitext(image_filename)[0] + ".txt"
                with open(os.path.join(lbl_dest, txt_filename), 'w', encoding='utf-8') as txt_f:
                    txt_f.write(yolo_line)
                
                total_processed += 1

            except Exception:
                continue

    print(f"[{split_name}] 완료! 총 {total_processed}장 저장됨.")

# ==========================================
# 4. 실행부
# ==========================================
if __name__ == "__main__":
    # 이미지 맵 생성
    train_image_map = build_image_folder_map(BASE_TRAIN_IMAGE)
    if not train_image_map:
        print("이미지 폴더를 못 찾았습니다.")
        exit()

    classes = sorted(list(train_image_map.keys()))
    class_to_id = {name: i for i, name in enumerate(classes)}
    
    print(f"감지된 클래스: {len(classes)}개")
    
    # yaml 생성
    yaml_content = f"""
path: {OUTPUT_DIR}
train: train/images
val: val/images

nc: {len(classes)}
names: {classes}
"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, 'data.yaml'), 'w', encoding='utf-8') as f:
        f.write(yaml_content)

    # Train 데이터 처리 (랜덤 샘플링 적용)
    process_dataset(BASE_TRAIN_LABEL, train_image_map, OUTPUT_DIR, 'train', class_to_id)
    
    # Validation 데이터 처리 (여기는 양이 적으니 그냥 다 하거나, 똑같이 제한)
    val_image_map = build_image_folder_map(BASE_VAL_IMAGE)
    process_dataset(BASE_VAL_LABEL, val_image_map, OUTPUT_DIR, 'val', class_to_id)
