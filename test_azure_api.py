import requests
import json
import time

def test_catvton_api():
    # 1. API 주소 설정 (kubectl get svc vfit-service 의 EXTERNAL-IP 를 사용합니다.)
    # 주의: catvtonaks-dns-m5vd1i7s.hcp... 주소는 Azure 인프라 관리용 주소이며 API 주소가 아닙니다!
    api_url = "http://4.217.129.126/api/v1/fit"
    
    # 2. 보안 키 설정 (.env의 API_SECRET_KEY 혹은 k8s secret 에 넣은 값)
    headers = {
        "x-api-key": "my_secure_portal_token_123",
        "Content-Type": "application/json"
    }
    
    # 3. Azure Blob 에 미리 저장해 둔 파일 경로 지정
    # payload = {
    #     "target_image_blob": "input/person/G8hd278akAAIj4X.jpg",   # 원본 사람 사진
    #     "garment_image_blob": "input/cloth/standardKnit.jpg", # 의류 사진
    #     "cloth_type": "upper"                           # 상의
    # }

    payload = {
        # 3dt1stteam3 storage account의 컨테이너 이름을 포함한 경로를 지정
        "target_image_blob": "catvton/input/person/man2.jpg",   
        "garment_image_blob": "catvton/input/cloth/cloth1.png",      
        # "bg_removed_blob": "segmentation/2f9be5aa08534d398fdf9320535b4a64_c53edcdaf4371be8a6496bf095b676f9_seg.png", 
        "cloth_type": "upper",       
        "output_path": "catvton/output" 
    }


    
    print(f"🚀 가상 피팅 GPU 서버로 요청을 보냅니다...")
    print(f"URL: {api_url}")
    print(f"데이터: {json.dumps(payload, indent=2)}")
    
    start_time = time.time()
    
    try:
        # POST 요청 전송
        response = requests.post(api_url, headers=headers, json=payload)
        
        print("\n--- 결과 응답 ---")
        print(f"HTTP Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result_data = response.json()
            print("✅ 피팅 성공!")
            print(f"결과 이미지 경로(Blob): {result_data.get('result_file')}")
            print(f"소요 시간: {time.time() - start_time:.2f} 초")
        else:
            print("❌ 피팅 실패!")
            print(f"에러 메시지: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다. (아직 GPU 파드가 뜨지 않았거나 IP가 틀렸습니다)")
        
if __name__ == "__main__":
    test_catvton_api()
