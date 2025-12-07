from ultralytics import YOLO
import torch
import os

if __name__ == '__main__':
    MODEL_PATH = r"C:\Users\rkdal\Desktop\학교\3-2\파이썬기반딥러닝\기말 프로젝트\Food_Detection_Project\train_result_300sample\weights\best.pt"
    DATA_PATH = r"D:\데이터셋\YOLO\datasets\data.yaml"

    save_folder = r"C:\Users\rkdal\Desktop\학교\3-2\파이썬기반딥러닝\기말 프로젝트\Food_Detection_Project"
    os.makedirs(save_folder, exist_ok=True)

    device = 0 if torch.cuda.is_available() else 'cpu'
    print(f"🔥 GPU 사용: {torch.cuda.get_device_name(0)}" if device == 0 else "⚠️ CPU 사용")

    model = YOLO(MODEL_PATH)

    num_classes = 571

    print("\n[Confusion Matrix 생성 중]")
    print("=> project/name 지정한 경로에 결과 저장됩니다.")

    metrics = model.val(
        data=DATA_PATH,
        split='val',
        imgsz=640,
        batch=16,
        workers=4,
        device=device,
        save_json=False,

        project=save_folder,
        name='confusion_matrix_by_id',

        plots=True,
        exist_ok=True
    )

    cm = getattr(metrics, "confusion_matrix", None)

    if cm is None:
        print("\nmetrics.confusion_matrix 를 찾을 수 없습니다. "
                "Ultralytics 버전을 확인해 주세요.")
    else:
        cm.names = {i: str(i) for i in range(num_classes)}

        cm_save_dir = os.path.join(save_folder, "confusion_matrix_by_id")
        os.makedirs(cm_save_dir, exist_ok=True)

        print("\n[숫자 ID 레이블 Confusion Matrix 재생성]")
        print(f"저장 경로: {cm_save_dir}")

        cm.plot(normalize=False, save_dir=cm_save_dir)
        cm.plot(normalize=True, save_dir=cm_save_dir)

        cm_png_path = os.path.join(cm_save_dir, "confusion_matrix.png")
        cm_norm_png_path = os.path.join(cm_save_dir, "confusion_matrix_normalized.png")

    print("\n" + "="*50)
    print("      ✅ Confusion Matrix 생성 완료 (숫자 ID 레이블) ✅")
    print("="*50)
    print(f"🔥 mAP50 (정확도): {metrics.box.map50*100:.2f}%")
    print(f"🔥 mAP50-95 (정교함): {metrics.box.map*100:.2f}%")
    print("🖼️ Confusion Matrix 이미지 저장 위치:")
    print(f"   -> {save_folder}\\confusion_matrix_by_id\\confusion_matrix.png")
    print(f"   -> {save_folder}\\confusion_matrix_by_id\\confusion_matrix_normalized.png")
    print("="*50)
