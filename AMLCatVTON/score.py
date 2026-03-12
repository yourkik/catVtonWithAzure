import os
import sys
import json
import logging
import uuid
from azure.storage.blob import BlobServiceClient

# Add parent directory to path to import process_fitting_job 
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

import process_fitting_job
import threading
import subprocess
import time
import requests

comfy_process = None

def init():
    """
    This function is called when the container is initialized/started.
    We will start the ComfyUI server in the background and wait for it to be ready.
    """
    global comfy_process
    logging.info("Initializing score.py: Starting ComfyUI backend...")
    
    comfyui_dir = os.path.join(parent_dir, "ComfyUI")
    if os.path.exists(comfyui_dir):
        # Start ComfyUI in the background
        comfy_process = subprocess.Popen(
            [sys.executable, "main.py", "--listen", "127.0.0.1", "--port", "8188"],
            cwd=comfyui_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        logging.info("ComfyUI subprocess launched. Waiting for it to boot...")
        
        # Wait until it's responsive
        max_retries = 30
        for i in range(max_retries):
            try:
                res = requests.get("http://127.0.0.1:8188/system_stats")
                if res.status_code == 200:
                    logging.info("ComfyUI server is up and responsive!")
                    break
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(2)
    else:
        logging.warning("ComfyUI directory not found. Assuming raw inference mode.")

def run(raw_data):
    """
    This function is called for every invocation of the endpoint.
    """
    logging.info(f"Received request: {raw_data}")
    try:
        data = json.loads(raw_data)
        
        # Ensure mandatory fields are present
        target_image_blob = data.get("target_image_blob")
        garment_image_blob = data.get("garment_image_blob")
        cloth_type = data.get("cloth_type", "upper")
        
        if not target_image_blob or not garment_image_blob:
            return json.dumps({"error": "Missing target_image_blob or garment_image_blob"})
            
        # Instead of calling the FastAPI route, we directly call the python logic 
        # that orchestrates the blob download, comfy execution, and blob upload!
        # Because we injected the connection string via env variables, azure_storage.py will work perfectly.
        
        # Process the job
        logging.info("Handing off to process_fitting_job...")
        result = process_fitting_job.process_fitting_job(target_image_blob, garment_image_blob, cloth_type)
        
        return json.dumps(result)
            
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error during run(): {error_msg}")
        return json.dumps({"error": error_msg})
