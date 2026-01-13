FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치 (필요할 경우)
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 포트 설정
EXPOSE 8000

# 서버 실행
CMD ["python", "server.py"]
