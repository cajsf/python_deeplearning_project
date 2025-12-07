from ultralytics import YOLO
import torch
import sys

if __name__ == '__main__':
    
    print(f"Python 버전: {sys.version}")
    if torch.cuda.is_available():
        print(f"🔥 GPU 가동! 모델명: {torch.cuda.get_device_name(0)}")
        device = 0
    else:
        print("⚠️ GPU를 찾을 수 없습니다. CPU로 학습하면 며칠이 걸릴 수 있습니다.")
        device = 'cpu'

    model = YOLO('yolov8s.pt') 

    results = model.train(
        data=r"D:\데이터셋\YOLO\datasets\data.yaml",
        epochs=30,
        patience=5,
        batch=16,
        imgsz=640,
        device=device,
        workers=4,
        cache=False,
        
        project='Food_Detection_Project',
        name='train_result_300sample',
        exist_ok=True, 
        
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=10.0,
        fliplr=0.5,
        flipud=0.0,
        mosaic=1.0,

        verbose=True
    )

    print("\n✅ 학습이 완료되었습니다!")
    print("결과 파일(best.pt)은 'Food_Detection_Project/train_result_300sample/weights' 폴더에 있습니다.")