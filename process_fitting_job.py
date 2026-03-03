import os
import json
import uuid
import time
from datetime import datetime
import urllib.request
import urllib.parse
import urllib.error
import urllib.response
import requests
import websocket
from azure_storage import download_from_azure, upload_to_azure
from dotenv import load_dotenv

# .env 로드
load_dotenv()

SERVER_ADDRESS = os.getenv('COMFYUI_SERVER_ADDRESS', '127.0.0.1:8188')
CLIENT_ID = str(uuid.uuid4())

# 로컬 임시 폴더
TEMP_DIR = "./temp_jobs"
os.makedirs(TEMP_DIR, exist_ok=True)

def queue_prompt(prompt):
    """ComfyUI 서버에 워크플로우(Prompt) 실행 요청"""
    p = {"prompt": prompt, "client_id": CLIENT_ID}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{SERVER_ADDRESS}/prompt", data=data)
    try:
        response = urllib.request.urlopen(req)
        return json.loads(response.read())
    except urllib.error.URLError as e:
        print(f"Failed to connect to ComfyUI server: {e}")
        return None

def upload_image(image_path):
    """ComfyUI 서버의 input 폴더로 이미지 업로드"""
    try:
        with open(image_path, "rb") as f:
            files = {"image": open(image_path, "rb")}
            res = requests.post(f"http://{SERVER_ADDRESS}/upload/image", files=files)
            if res.status_code == 200:
                print(f"Successfully uploaded {os.path.basename(image_path)} to ComfyUI.")
                return res.json()['name']
            else:
                print(f"Failed to upload {image_path}. Status: {res.status_code}")
                return None
    except Exception as e:
        print(f"Exception during upload: {e}")
        return None

def get_image(filename, subfolder, folder_type):
    """ComfyUI 서버에서 결과 이미지(바이너리) 가져오기"""
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen(f"http://{SERVER_ADDRESS}/view?{url_values}") as response:
        return response.read()

def get_history(prompt_id):
    """특정 Prompt ID의 실행 결과(히스토리) 가져오기"""
    with urllib.request.urlopen(f"http://{SERVER_ADDRESS}/history/{prompt_id}") as response:
        return json.loads(response.read())

def get_images_from_ws(prompt_dict, prompt_id):
    """
    WebSocket을 통해 작업 진행 상황을 모니터링하고, 
    작업이 완료되면 히스토리에서 결과 이미지를 추출해 로컬에 다운로드합니다.
    """
    try:
        ws = websocket.WebSocket()
        ws.connect(f"ws://{SERVER_ADDRESS}/ws?clientId={CLIENT_ID}")
        
        images_output = {}
        
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        # 실행 완료
                        break
            else:
                # 바이너리 데이터(진행중인 프리뷰 이미지 텐서 등)는 여기서는 무시
                continue
                
        ws.close()
        print("Workflow execution completed. Fetching results...")
        
        # 히스토리 API를 통해 최종 결과물 확인
        history = get_history(prompt_id)
        if not history or prompt_id not in history:
            print("Failed to get history for prompt_id")
            return {}
            
        outputs = history[prompt_id].get('outputs', {})
        
        for node_id, node_output in outputs.items():
            if 'images' in node_output:
                images_output[node_id] = []
                for image in node_output['images']:
                    image_data = get_image(image['filename'], image['subfolder'], image['type'])
                    images_output[node_id].append((image['filename'], image_data))
                    
        return images_output
    except Exception as e:
        print(f"WebSocket Error: {e}")
        return {}

def process_fitting_job(target_image_blob: str, garment_image_blob: str, cloth_type: str = "overall"):
    """
    하나의 가상 피팅 작업을 처리하는 메인 파이프라인 함수
    - cloth_type: 'overall', 'upper', 'lower' 중 선택
    1. 원본 이미지 다운로드 (Azure -> Local)
    2. ComfyUI 업로드 및 Workflow JSON 수정
    3. 추론 실행
    4. 결과 수신 (ComfyUI -> Local)
    5. 결과 업로드 (Local -> Azure)
    
    Returns:
        dict: 성공 시 {"success": True, "result_file": final_blob_name} 반환
              실패 시 {"success": False, "error": 에러메시지} 반환
    """
    
    # 올바른 의류 타입 검증
    valid_types = ["overall", "upper", "lower"]
    if cloth_type not in valid_types:
        cloth_type = "overall"

    print(f"--- Starting fitting job ---")
    print(f"Target: {target_image_blob}, Garment: {garment_image_blob}, Cloth Type: {cloth_type}")
    
    # 추출: 사람 이미지 이름, 의류 이미지 이름 (확장자 제외)
    target_base_name = os.path.splitext(os.path.basename(target_image_blob))[0]
    garment_base_name = os.path.splitext(os.path.basename(garment_image_blob))[0]
    
    # 1. 다운로드
    target_local_path = os.path.join(TEMP_DIR, os.path.basename(target_image_blob))
    garment_local_path = os.path.join(TEMP_DIR, os.path.basename(garment_image_blob))
    
    if not download_from_azure(target_image_blob, target_local_path):
        return {"success": False, "error": f"Failed to download {target_image_blob} from Azure"}
    if not download_from_azure(garment_image_blob, garment_local_path):
        return {"success": False, "error": f"Failed to download {garment_image_blob} from Azure"}
        
    # 2. ComfyUI에 파일 업로드 (중복 파일명 방지를 위해 유니크한 이름으로 업로드해도 되지만 그대로 진행)
    uploaded_target_name = upload_image(target_local_path)
    uploaded_garment_name = upload_image(garment_local_path)
    
    if not uploaded_target_name or not uploaded_garment_name:
        return {"success": False, "error": "Failed to upload input images to ComfyUI server"}
        
    # 3. 워크플로우 준비
    workflow_path = "D:/학업 관련 파일/자료 모음/dataSchool/1차프로젝트/가상피팅/ComfyUI/catvton_workflow_api.json"
    
    try:
        with open(workflow_path, "r", encoding="utf-8") as f:
            api_prompt = json.load(f)
            
        # Target Person (Node 10), Reference Garment (Node 11) 파일명 업데이트
        if "10" in api_prompt and api_prompt["10"]["class_type"] == "LoadImage":
            api_prompt["10"]["inputs"]["image"] = uploaded_target_name
            
        if "11" in api_prompt and api_prompt["11"]["class_type"] == "LoadImage":
            api_prompt["11"]["inputs"]["image"] = uploaded_garment_name
            
        # AutoMasker (Node 13) 옷 종류 (overall, upper, lower) 업데이트
        if "13" in api_prompt and api_prompt["13"]["class_type"] == "AutoMasker":
            api_prompt["13"]["inputs"]["cloth_type"] = cloth_type

        # 추가로 결과 저장을 위한 SaveImage 노드를 덧붙이거나,
        # PreviewImage 노드 (Node 18)의 데이터를 히스토리에서 바로 뽑아 쓸 수 있습니다.
        # 여기서는 웹소켓 모니터링 후 PreviewImage 노드의 결과물을 빼오도록 합니다.
            
    except Exception as e:
        return {"success": False, "error": f"Error modifying workflow JSON: {str(e)}"}

    # 4. 프롬프트(워크플로우) 실행 요청
    print("Executing workflow...")
    prompt_res = queue_prompt(api_prompt)
    if not prompt_res:
        return {"success": False, "error": "ComfyUI prompt request failed"}
        
    prompt_id = prompt_res['prompt_id']
    print(f"Prompt queued. ID: {prompt_id}")
    
    # 5. 결과 대기 및 다운로드
    output_images = get_images_from_ws(api_prompt, prompt_id)
    
    # CatVTON의 최종 결과물 노드는 PreviewImage (Node 18) 입니다.
    catvton_result_node_id = "18"
    
    if catvton_result_node_id in output_images and len(output_images[catvton_result_node_id]) > 0:
        output_filename, output_data = output_images[catvton_result_node_id][0]
        
        # 날짜 및 시간 포맷 가져오기 (YYYYMMDD_HH 형식)
        ymdh = datetime.now().strftime("%Y%m%d_%H")
        
        # 파일명 생성: result_{YYYYMMDD_HH}_{만 이름}_{옷 이름}.png
        final_filename = f"result_{ymdh}_{target_base_name}_{garment_base_name}_{cloth_type}.png"
        
        # 로컬 저장 및 업로드 경로 지정
        final_local_path = os.path.join(TEMP_DIR, final_filename)
        final_blob_name = f"output/{final_filename}"
        
        with open(final_local_path, "wb") as f:
            f.write(output_data)
        print(f"Final output saved locally to: {final_local_path}")
        
        # 6. 결과 업로드 (Local -> Azure)
        upload_success = upload_to_azure(final_local_path, final_blob_name)
        
        # 정리 작업
        try:
            os.remove(target_local_path)
            os.remove(garment_local_path)
            os.remove(final_local_path)
            print("Temporary files cleaned up.")
        except OSError as e:
            print(f"Error cleaning up temp files: {e}")
            
        if upload_success:
            return {"success": True, "result_file": final_blob_name}
        else:
            return {"success": False, "error": "Failed to upload final image to Azure Storage"}
    else:
        return {"success": False, "error": "Failed to retrieve the final output image from the workflow"}

if __name__ == "__main__":
    print("ComfyUI-Azure Automation Script Ready.")
    # 실제 연동 시 아래와 같이 호출합니다. (의류 형태 선택 시: overall, upper, lower)
    # process_fitting_job("input/person/man2.jpg", "input/cloth/cloth1.png", cloth_type="upper")
    process_fitting_job("input/person/man2.jpg", "input/cloth/cloth1.png", cloth_type="upper")
