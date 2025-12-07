import os
import requests
import pymysql
import time
import random
from io import BytesIO
from PIL import Image # 이미지 처리를 위한 모듈

# ==========================================
# [설정] DB 및 저장 경로
# ==========================================
SAVE_DIR = "static/food_images"
os.makedirs(SAVE_DIR, exist_ok=True)

db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '1234',
    'database': 'Food_Allergy_DB',
    'port': 3306
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.otokimall.com/'
}

def download_and_convert_to_webp():
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()

    try:
        print("🔍 WebP 변환을 위해 다운로드할 목록을 조회합니다...")
        sql = "SELECT food_id, food_name, food_img_url FROM Food WHERE food_img_url LIKE 'http%'"
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        print(f"총 {len(rows)}개의 이미지를 처리합니다.")

        for idx, row in enumerate(rows, start=1):
            food_id = row[0]
            name = row[1]
            url = row[2]

            filename = f"food_{food_id}.webp"
            save_path = os.path.join(SAVE_DIR, filename)

            web_path = f"/{SAVE_DIR}/{filename}"

            try:
                print(f"[{idx}/{len(rows)}] 변환 중: {name} ...", end=" ")
                
                resp = requests.get(url, headers=HEADERS, timeout=10)
                
                if resp.status_code == 200:
                    image_data = BytesIO(resp.content)
                    img = Image.open(image_data)
                    
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGBA")
                    else:
                        img = img.convert("RGB")

                    img.save(save_path, 'WEBP', quality=80)
                    
                    update_sql = "UPDATE Food SET food_img_url = %s WHERE food_id = %s"
                    cursor.execute(update_sql, (web_path, food_id))
                    conn.commit()
                    print("✅ 성공 (WebP 저장 완료)")
                else:
                    print(f"다운로드 실패 (Status: {resp.status_code})")

            except Exception as e:
                print(f"변환 에러: {e}")

            time.sleep(random.uniform(0.1, 0.3))

        print("\n모든 작업 완료! 이미지가 WebP로 최적화되었습니다.")
    finally:
        conn.close()

if __name__ == "__main__":
    download_and_convert_to_webp()