from ultralytics import YOLO
import cv2
import matplotlib.pyplot as plt

# 1. 모델 로드
model_path = r"C:\Users\rkdal\Desktop\학교\3-2\파이썬기반딥러닝\기말 프로젝트\Food_Detection_Project\train_result_300sample\weights\best.pt"
model = YOLO(model_path)

# 2. 이미지 예측
source_image = r"C:\Users\rkdal\Downloads\갈비탕.jpg" # 테스트할 이미지 경로 확인!
results = model.predict(source=source_image, save=True, conf=0.25)

# 3. 결과 확인 (화면 팝업 ❌ -> 저장된 경로 안내 ⭕)
print("\n✅ 예측이 완료되었습니다!")
print(f"▶ 결과 이미지는 'runs/detect/predict' 폴더에 저장되었습니다.")

# 터미널에 텍스트로만 결과 출력 (에러 안 남)
for result in results:
    print("\n🍽️ 감지된 음식 목록:")
    for box in result.boxes:
        class_id = int(box.cls[0])
        conf = float(box.conf[0])
        food_name = result.names[class_id]
        print(f" - {food_name} (정확도: {conf*100:.1f}%)")