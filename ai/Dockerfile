FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    git \
    xvfb \
    python3-tk \
    libx11-dev \
    libxtst6 \
    && rm -rf /var/lib/apt/lists/*

ENV DISPLAY=:99

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 포트 설정
EXPOSE 8000

# 서버 실행 (가상 디스플레이 설정)
CMD ["xvfb-run", "--server-args=-screen 0 1024x768x24", "python", "server.py"]
