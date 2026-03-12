FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# 불필요한 상호작용 방지
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 1. 필수 기본 패키지 및 Python 3.10 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3.10-venv \
    git \
    wget \
    curl \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# python 명령어를 python3.10으로 연결
RUN ln -sf /usr/bin/python3.10 /usr/bin/python \
    && ln -sf /usr/bin/python3.10 /usr/bin/python3

WORKDIR /app

# 2. FastAPI 및 백엔드 의존성 먼저 복사 후 설치 (캐싱용)
# 루트에 별도 requirements.txt가 없으니 직접 설치합니다
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    python-dotenv \
    pydantic \
    requests \
    websocket-client \
    azure-storage-blob \
    python-multipart

# 3. ComfyUI 전용 PyTorch 및 의존성 설치
# CUDA 12.1 에 맞는 버전 설치
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 4. 전체 앱 복사 (.dockerignore 적용됨)
COPY . /app

# 4.1. 외부 폴더(서브모듈) 동적 다운로드 (Git Option 2)
# .gitignore 로 제외된 3rd-party 폴더들을 컨테이너 빌드 시 원본에서 직접 다운로드
RUN rmdir /app/CatVTON /app/ComfyUI /app/Re-CatVTON 2>/dev/null || true && \
    git clone https://github.com/Zheng-Chong/CatVTON.git /app/CatVTON && \
    git clone https://github.com/comfyanonymous/ComfyUI.git /app/ComfyUI && \
    git clone https://github.com/Levinna/Re-CatVTON.git /app/Re-CatVTON && \
    git clone https://github.com/huzhanzhou/ComfyUI-CatVTON.git /app/ComfyUI/custom_nodes/ComfyUI-CatVTON

# 루트 폴더의 전체 의존성 먼저 설치
RUN if [ -f "/app/requirements.txt" ]; then pip install --no-cache-dir -r /app/requirements.txt; fi

# ComfyUI의 requirements.txt가 존재하면 설치
RUN if [ -f "/app/ComfyUI/requirements.txt" ]; then pip install --no-cache-dir -r /app/ComfyUI/requirements.txt; fi

# 가상 피팅(CatVTON 등) 커스텀 노드가 있다면 해당 노드의 requirements.txt 도 존재 시 추가 처리
RUN for req in $(find /app/ComfyUI/custom_nodes -name 'requirements.txt'); do pip install --no-cache-dir -r $req; done

# 5. 실행 스크립트 권한 부여 및 진입점 설정
RUN chmod +x /app/startup.sh

EXPOSE 8000

# 컨테이너 시작 시 startup.sh 실행
CMD ["/app/startup.sh"]
