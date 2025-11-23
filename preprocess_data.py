import json
import os
import glob
from tqdm import tqdm

def process_dataset_exact_path(annotation_dir, image_dir, output_dir, category_name):
    # 1. 출력 폴더 생성
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"폴더 생성됨: {output_dir}")
    
    # 2. 이미지 폴더 존재 확인
    if not os.path.exists(image_dir):
        print(f"\n[오류] 이미지 폴더를 찾을 수 없습니다: {image_dir}")
        print("경로를 다시 확인해주세요.")
        return

    # 3. JSON 파일 목록 가져오기
    json_files = glob.glob(os.path.join(annotation_dir, "*.json"))
    print(f"\n[{category_name}] 처리 시작")
    print(f" - 라벨링 폴더: {annotation_dir}")
    print(f" - 이미지 폴더: {image_dir}")
    print(f" - 파일 개수: {len(json_files)}개")

    processed_count = 0

    for json_path in tqdm(json_files, desc=f"{category_name} 변환 중"):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 이미지 파일명 확인
            if not data.get('images'):
                continue
                
            image_info = data['images'][0]
            image_filename = image_info['name']
            
            # [핵심 수정] 사용자가 지정한 이미지 폴더 경로와 파일명 결합
            image_full_path = os.path.join(image_dir, image_filename)
            
            # 윈도우 경로(\) 호환성 처리
            image_full_path = image_full_path.replace("\\", "/")

            # 텍스트 블록 추출 및 정렬
            text_blocks = []
            if 'annotations' in data:
                for annotation in data['annotations']:
                    if 'polygons' not in annotation:
                        continue
                        
                    for poly in annotation['polygons']:
                        if 'text' not in poly or 'points' not in poly:
                            continue
                        
                        # type 0 (식별불가) 제외 [참조: 소스 92]
                        poly_type = str(poly.get('type', '1')) 
                        if poly_type == '0': 
                            continue

                        points = poly['points']
                        if not points:
                            continue
                            
                        y_coords = points[1::2]
                        x_coords = points[0::2]
                        
                        min_y = min(y_coords) if y_coords else 0
                        min_x = min(x_coords) if x_coords else 0
                        
                        text_blocks.append({
                            "text": poly['text'],
                            "y": min_y,
                            "x": min_x
                        })

            # 정렬: Y축(위->아래) 우선, X축(좌->우) 차선
            text_blocks.sort(key=lambda k: (k['y'], k['x']))

            full_text = "\n".join([b['text'] for b in text_blocks])

            if not full_text.strip():
                continue

            # Qwen 학습용 포맷
            qwen_format = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "image": image_full_path},
                            {"type": "text", "text": "이미지 내의 모든 텍스트(제품명, 성분표, 설명 등)를 보이는 순서대로 추출해줘."}
                        ]
                    },
                    {
                        "role": "assistant",
                        "content": full_text
                    }
                ]
            }

            # 개별 파일 저장
            output_filename = os.path.basename(json_path)
            output_path = os.path.join(output_dir, output_filename)

            with open(output_path, 'w', encoding='utf-8') as out_f:
                json.dump(qwen_format, out_f, ensure_ascii=False, indent=2)
            
            processed_count += 1

        except Exception as e:
            print(f"Error processing {json_path}: {e}")

    print(f"[{category_name}] 완료! {processed_count}개 저장됨.")

# --- [경로 설정 부분] ---
if __name__ == "__main__":
    # 1. 화장품 (Cosmetics)
    # 원천데이터 경로가 라벨링데이터와 다름을 반영
    cosmetics_anno_dir = r"D:\데이터셋\01.데이터\2. Validation\라벨링데이터\cosmetics\annotations"
    cosmetics_img_dir  = r"D:\데이터셋\01.데이터\2. Validation\원천데이터\cosmetics\images"
    cosmetics_out_dir  = r"D:\데이터셋\01.데이터\2. Validation\라벨링데이터\cosmetics\annotations_preprocessing"

    process_dataset_exact_path(cosmetics_anno_dir, cosmetics_img_dir, cosmetics_out_dir, "화장품")
    
    # 2. 의약품 (Medicine)
    # 의약품도 같은 구조일 것으로 가정하고 경로 설정
    medicine_anno_dir = r"D:\데이터셋\01.데이터\2. Validation\라벨링데이터\medicine\annotations"
    medicine_img_dir  = r"D:\데이터셋\01.데이터\2. Validation\원천데이터\medicine\images"
    medicine_out_dir  = r"D:\데이터셋\01.데이터\2. Validation\라벨링데이터\medicine\annotations_preprocessing"
    
    process_dataset_exact_path(medicine_anno_dir, medicine_img_dir, medicine_out_dir, "의약품")