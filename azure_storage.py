import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경 변수에서 연결 문자열과 컨테이너 이름 가져오기
CONNECT_STR = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
INPUT_CONTAINER = os.getenv('INPUT_CONTAINER_NAME', 'catvton')
OUTPUT_CONTAINER = os.getenv('OUTPUT_CONTAINER_NAME', 'catvton')

if not CONNECT_STR:
    raise ValueError("AZURE_STORAGE_CONNECTION_STRING is not set in the .env file.")

# BlobServiceClient 초기화
blob_service_client = BlobServiceClient.from_connection_string(CONNECT_STR)

def download_from_azure(blob_name: str, download_path: str, container_name: str = INPUT_CONTAINER) -> bool:
    """
    Azure Blob Storage에서 특정 파일을 다운로드합니다.
    """
    try:
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        
        # 다운로드할 폴더가 없다면 생성
        os.makedirs(os.path.dirname(download_path), exist_ok=True)
        
        print(f"[{container_name}] Downloading {blob_name} to {download_path}...")
        with open(download_path, "wb") as download_file:
            download_file.write(blob_client.download_blob().readall())
        print(f"Download completed: {download_path}")
        return True
    except Exception as e:
        print(f"Error downloading {blob_name} from Azure: {e}")
        return False

def upload_to_azure(file_path: str, blob_name: str, container_name: str = OUTPUT_CONTAINER) -> bool:
    """
    로컬 파일을 Azure Blob Storage에 업로드합니다.
    """
    try:
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        
        print(f"[{container_name}] Uploading {file_path} to {blob_name}...")
        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        print(f"Upload completed: {blob_name}")
        return True
    except Exception as e:
        print(f"Error uploading {file_path} to Azure: {e}")
        return False
