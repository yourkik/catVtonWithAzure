from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import process_fitting_job
import urllib.request
import urllib.parse
import urllib.error

# Load environment variables
load_dotenv()
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "your_secret_key_here")

app = FastAPI(title="CatVTON Virtual Fitting API")

# Add CORS so a portal can call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class FittingRequest(BaseModel):
    target_image_blob: str
    garment_image_blob: str
    cloth_type: str = "overall" # allow: "overall", "upper", "lower"

# Dependency to check API Key
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key

@app.get("/")
def read_root():
    return {"status": "Virtual Fitting API is running."}

@app.post("/api/v1/fit")
async def run_fitting_job(request: FittingRequest, api_key: str = Depends(verify_api_key)):
    """
    Triggers the process_fitting_job pipeline.
    """
    result = process_fitting_job.process_fitting_job(
        target_image_blob=request.target_image_blob,
        garment_image_blob=request.garment_image_blob,
        cloth_type=request.cloth_type
    )
    
    if not result:
        # Fallback if somehow it returns None
        raise HTTPException(status_code=500, detail="Unknown pipeline error")
        
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to process image"))
        
    return {
        "success": True,
        "result_file": result.get("result_file")
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
