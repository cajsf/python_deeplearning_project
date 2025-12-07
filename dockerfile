FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    build-essential \
    libglib2.0-0 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# pip 최신화
RUN pip3 install --upgrade pip

# 파이썬 라이브러리 설치
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# 프로젝트 전체 복사
COPY . .

# FastAPI 포트 오픈
EXPOSE 8000

CMD ["python3", "-m", "uvicorn", "api_main:app", "--host", "0.0.0.0", "--port", "8000"]
