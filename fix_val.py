import os
import json
import shutil
import random
from tqdm import tqdm

# ==========================================
# 1. 설정 (검증용은 50장이면 충분!)
# ==========================================
MAX_VAL_IMAGES = 30 # 기존 제한 없음 -> 50장으로 축소

# 경로 설정 (아까랑 똑같이)
BASE_TRAIN_IMAGE = r"E:\데이터셋\건강관리를 위한 음식 이미지\Training\원천" # 클래스 순서 맞추기용
BASE_VAL_LABEL = r"E:\데이터셋\건강관리를 위한 음식 이미지\Validation\라벨"
BASE_VAL_IMAGE = r"E:\데이터셋\건강관리를 위한 음식 이미지\Validation\원천"
OUTPUT_DIR = r"E:\YOLO\datasets"

# ==========================================
# 2. 유틸리티 함수
# ==========================================
def build_image_folder_map(image_root):
    # 폴더 지도 만들기
    folder_map = {}
    for root, dirs, files in os.walk(image_root):
        folder_name = os.path.basename(root)
        has_image = any(f.lower().endswith(('.jpg', '.jpeg', '.png')) for f in files)
        if has_image:
            folder_map[folder_name] = root
    return folder_map

def process_val_only(label_root, image_folder_map, output_root, class_to_id):
    # 1. 기존 무거운 val 폴더 삭제 (수술 시작)
    val_path = os.path.join(output_root, 'val')
    if os.path.exists(val_path):
        print(f"🗑️ 기존의 무거운 Validation 폴더를 삭제합니다... ({val_path})")
        shutil.rmtree(val_path)
    
    # 2. 폴더 다시 생성
    img_dest = os.path.join(output_root, 'val', 'images')
    lbl_dest = os.path.join(output_root, 'val', 'labels')
    os.makedirs(img_dest, exist_ok=True)
    os.makedirs(lbl_dest, exist_ok=True)

    print(f"\n🚀 [Validation] 데이터 재구축 시작 (최대 {MAX_VAL_IMAGES}장 제한)...")
    
    total_processed = 0
    pbar = tqdm(desc="Validation 처리 중", unit="장")
    
    for root, dirs, files in os.walk(label_root):
        json_files = [f for f in files if f.endswith('.json')]
        if not json_files: continue

        label_folder_name = os.path.basename(root)
        clean_name = label_folder_name.replace(" json", "").replace("_json", "").strip()
        
        target_image_dir = image_folder_map.get(clean_name)
        if not target_image_dir: target_image_dir = image_folder_map.get(label_folder_name)
        
        if not target_image_dir or clean_name not in class_to_id: continue
        class_id = class_to_id[clean_name]

        # ==========================================
        # [핵심] 50장만 랜덤 샘플링 (다이어트!)
        # ==========================================
        if len(json_files) > MAX_VAL_IMAGES:
            selected_files = random.sample(json_files, MAX_VAL_IMAGES)
        else:
            selected_files = json_files

        for filename in selected_files:
            try:
                json_path = os.path.join(root, filename)
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list): data = data[0]

                image_filename = os.path.splitext(filename)[0] + ".jpg"
                src_image_path = os.path.join(target_image_dir, image_filename)
                
                # 이미지 확장자 찾기
                if not os.path.exists(src_image_path):
                    if os.path.exists(src_image_path.replace(".jpg", ".JPG")):
                        src_image_path = src_image_path.replace(".jpg", ".JPG")
                    elif os.path.exists(src_image_path.replace(".jpg", ".jpeg")):
                        src_image_path = src_image_path.replace(".jpg", ".jpeg")
                    else: continue 

                w, h = float(data['W']), float(data['H'])
                points = data['Point(x,y)'].split(',')
                x, y = float(points[0]), float(points[1])
                
                yolo_line = f"{class_id} {x} {y} {w} {h}\n"
                
                # 복사
                shutil.copy2(src_image_path, os.path.join(img_dest, image_filename))
                
                txt_filename = os.path.splitext(image_filename)[0] + ".txt"
                with open(os.path.join(lbl_dest, txt_filename), 'w', encoding='utf-8') as txt_f:
                    txt_f.write(yolo_line)
                
                total_processed += 1
                pbar.update(1)
            except: continue
    
    pbar.close()
    print(f"✅ Validation 재구축 완료! 총 {total_processed}장 (훨씬 가벼워짐!)")

if __name__ == "__main__":
    # 1. 클래스 ID 순서 확보 (Train 데이터 기준)
    # *중요* Train 폴더의 순서와 똑같아야 하므로, Train 원천 폴더를 한 번 스캔합니다.
    # (이미지 복사는 안 하고 목록만 가져오니까 금방 끝납니다)
    print("📋 클래스 목록 동기화 중...")
    train_map = build_image_folder_map(BASE_TRAIN_IMAGE)
    classes = sorted(list(train_map.keys()))
    class_to_id = {name: i for i, name in enumerate(classes)}
    
    # 2. Validation 지도 만들기
    print("🗺️ Validation 폴더 지도 생성 중...")
    val_map = build_image_folder_map(BASE_VAL_IMAGE)
    
    # 3. 수술 시작
    process_val_only(BASE_VAL_LABEL, val_map, OUTPUT_DIR, class_to_id)