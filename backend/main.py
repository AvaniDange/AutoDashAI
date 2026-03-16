import os
import uvicorn
import pandas as pd
import tempfile
import json
import io
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from dashboard_agent import DashboardAgent
from file_conversion import FileConverter

# Initialize Agents
dashboard_agent = DashboardAgent()
converter = FileConverter()

# ==================== FastAPI App ====================
app = FastAPI(title="AutoDash AI Full Stack API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ==================== Dashboard API ====================

class ChatRequest(BaseModel):
    session_id: str
    message: str

@app.post("/api/dashboard/chat")
async def chat_endpoint(req: ChatRequest):
    print(f"Chat request for session {req.session_id}: {req.message}")
    result = dashboard_agent.process_prompt(req.session_id, req.message)
    return result



@app.post("/api/dashboard/start")
async def start_dashboard(file: UploadFile = File(...)):
    print(f"Starting dashboard session with {file.filename}")
    try:
        content = await file.read()
        filename = file.filename.lower()
        
        print(f"DEBUG: File size: {len(content)} bytes")
        
        if filename.endswith(('.xlsx', '.xls')):
            print("DEBUG: Reading as Excel")
            df = pd.read_excel(io.BytesIO(content))
        else:
            print("DEBUG: Reading as CSV")
            df = pd.read_csv(io.BytesIO(content))
            
        print(f"DEBUG: Dataframe shape: {df.shape}")
        
        # Basic cleaning
        df = df.dropna(how='all', axis=1).dropna(how='all', axis=0)
        
        # Ensure we have data
        if df.empty:
            raise ValueError("Uploaded file contains no valid data")
            
        print("DEBUG: Initializing session...")
        session_id, charts, kpis, cols, slicers, pages = dashboard_agent.start_session(df)
        print("DEBUG: Session initialized successfully")
        
        return {
            "success": True,
            "session_id": session_id,
            "charts": charts,
            "kpis": kpis,
            "columns": cols,
            "slicers": slicers,
            "pages": pages,
            "theme": "light"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error starting dashboard: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": f"{type(e).__name__}: {str(e)}"})

# ==================== File Conversion API (Restored) ====================

@app.post("/process-files")
async def process_files(files: list[UploadFile] = File(...)):
    combined_results = []
    
    for uploaded_file in files:
        temp_path = None
        try:
            content = await uploaded_file.read()
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{uploaded_file.filename}") as tmp:
                tmp.write(content)
                temp_path = tmp.name
            
            result = converter.process_file(temp_path)
            
            if result['success']:
                df_dict = result['dataframe'].fillna("").to_dict(orient='records') if result['dataframe'] is not None else []
                combined_results.append({
                    "success": True,
                    "filename": uploaded_file.filename,
                    "dataframe": df_dict,
                    "columns": result['dataframe'].columns.tolist() if result['dataframe'] is not None else [],
                    "rows": len(result['dataframe']) if result['dataframe'] is not None else 0
                })
            else:
                combined_results.append({
                    "success": False,
                    "filename": uploaded_file.filename,
                    "error": result['error']
                })
                
        except Exception as e:
            combined_results.append({
                "success": False,
                "filename": uploaded_file.filename,
                "error": str(e)
            })
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except: pass

    return combined_results

# ==================== Main Execution ====================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
