# Virtual Fitting Automation API (CatVTON + ComfyUI + Azure) 👕✨

이 프로젝트는 **CatVTON** 기반의 가상 피팅(Virtual Try-On) 워크플로우를 **ComfyUI** 환경에서 구동하고, 이를 외부 서비스(Portal 등)에서 손쉽게 호출할 수 있도록 돕는 **FastAPI 백엔드 서버**입니다. 
입력과 출력 이미지는 모두 **Azure Blob Storage**를 통해 관리됩니다.

## 🌟 주요 기능 (Features)
1. **Azure Storage 연동**: Azure Blob Storage에서 사람 이미지와 옷 이미지를 자동으로 다운로드하고, 완료된 피팅 결과물을 지정된 경로(`output/{YYYYMMDD_HH}_{man}_{cloth}_{type}.png`)로 다시 업로드합니다.
2. **ComfyUI 파이프라인 자동화**: API 통신 및 WebSocket을 활용하여 ComfyUI 프롬프트를 큐(Queue)에 넣고, 변환 작업의 상태를 모니터링하여 최종 이미지를 추출합니다.
3. **가상 피팅 의류 타입 선택**: 전신(`overall`), 상의(`upper`), 하의(`lower`) 중 원하는 의류 적용 형태를 선택할 수 있습니다.
4. **FastAPI & Ngrok 터널링**: 외부 포털 웹사이트에서 로컬의 ComfyUI 환경을 안전하게 호출할 수 있도록 `FastAPI` 기반의 REST API 엔드포인트를 제공하며, `API Key` 인증으로 보안을 강화했습니다.

## 🏗️ 아키텍처 및 폴더 구조
```text
├── main.py                   # FastAPI 애플리케이션 진입점 (REST API 서버)
├── process_fitting_job.py    # 핵심 파이프라인 (Azure 다운로드 -> ComfyUI 전송 -> 결과 수신 -> Azure 업로드)
├── azure_storage.py          # Azure Blob Storage 업로드/다운로드 유틸리티
├── .env                      # [보안] 환경변수 (Azure 토큰, API Key 등 설정)
├── test.js                   # 포털(Frontend)에서 API를 호출하는 JS/Fetch 테스트 코드
└── temp_jobs/                # (자동생성) 작업 진행 중 이미지 다운로드/업로드를 처리하는 로컬 임시 폴더
```

## 🚀 시작하기 (Getting Started)

### 1. 환경 변수 설정
이 프로젝트의 루트 경로에 `.env` 파일을 생성하고 다음 변수들을 입력합니다.
```env
# Azure Storage 연결 계정 정보
AZURE_STORAGE_CONNECTION_STRING="your_azure_connection_string_here"

# 컨테이너 이름 (입출력 동일한 경우)
INPUT_CONTAINER_NAME="catvton"
OUTPUT_CONTAINER_NAME="catvton"

# 구동 중인 로컬 ComfyUI 주소
COMFYUI_SERVER_ADDRESS="127.0.0.1:8188"

# 외부 API 호출 시 사용할 비밀번호(API Key)
API_SECRET_KEY="my_secure_portal_token_123"
```

### 2. 패키지 설치
서버 구동에 필요한 파이썬 라이브러리들을 설치합니다.
```bash
pip install fastapi uvicorn pydantic requests websocket-client azure-storage-blob python-dotenv
```

### 3. 서버 실행
**주의:** 먼저 백그라운드에서 ComfyUI 서버가 구동 중이어야 합니다.
그 다음 `main.py` 리스너를 실행하여 포털의 요청을 대기합니다.
```bash
uvicorn main:app --port 8000
```
*(외부 노출이 필요한 경우 새로운 터미널을 열고 `ngrok http 8000` 을 실행하여 터널링 주소를 획득합니다.)*

## 📝 API 명세 (API Specification)

### `POST /api/v1/fit`
포털에서 가상 피팅 작업을 요청하는 엔드포인트입니다.

#### 요청 (Request)
* **Headers**
  * `Content-Type`: `application/json`
  * `x-api-key`: `.env`에 설정한 `API_SECRET_KEY` 문자열
  * `ngrok-skip-browser-warning`: `true` (Ngrok 사용 시 필수)
* **Body (JSON)**
  ```json
  {
    "target_image_blob": "input/person/man2.jpg",
    "garment_image_blob": "input/cloth/cloth1.png",
    "cloth_type": "upper" 
  }
  ```
  * `cloth_type`: `"overall"`, `"upper"`, `"lower"` 중 택 1.

#### 응답 (Response)
* **성공 시 (200 OK)**
  ```json
  {
    "success": true,
    "result_file": "output/result_20260303_16_man2_cloth1_upper.png"
  }
  ```
* **실패 시 (500 Internal Error)**
  ```json
  {
    "success": false,
    "detail": "Failed to upload final image to Azure Storage / Blob not found 등 상세 에러 리턴"
  }
  ```
