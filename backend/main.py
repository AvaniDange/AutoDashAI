import os
import argparse
import json
import re
import uvicorn
import pandas as pd
import numpy as np
import io
import tempfile
import base64
import glob
import shutil
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Body, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.encoders import jsonable_encoder

from backend.file_conversion import FileConverter
from backend.data_cleaner import detect_issues, clean_data, safe_json  # keep your existing cleaner

# Initialize the file converter
converter = FileConverter()

# ==================== FastAPI App ====================
app = FastAPI(title="AutoDash AI Full Stack API")

# Allow frontend CORS access
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ==================== Helper Functions ====================
async def process_uploaded_file(uploaded_file: UploadFile):
    """Process uploaded file and return structured data"""
    print(f"DEBUG: Processing file: {uploaded_file.filename}")
    temp_path = None
    try:
        # Save uploaded file to a temporary location outside the watched directory
        file_content = await uploaded_file.read()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{uploaded_file.filename}") as tmp:
            tmp.write(file_content)
            temp_path = tmp.name
        
        print(f"DEBUG: Temporary file created at: {temp_path}")

        try:
            # Process the file
            result = converter.process_file(temp_path)
            print(f"DEBUG: File processing success: {result['success']}")
        finally:
            # Clean up temporary file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    print(f"DEBUG: Cleaned up temp file: {temp_path}")
                except Exception as e:
                    print(f"DEBUG: Failed to clean up temp file: {e}")

        if result['success']:
            response_data = {
                "success": True,
                "filename": uploaded_file.filename,
                "has_structured_data": result['dataframe'] is not None and not result['dataframe'].empty,
                "has_text_content": result['text_content'] is not None and result['text_content'] != "",
            }

            if response_data['has_structured_data']:
                # Convert dataframe to serializable format
                df_dict = result['dataframe'].fillna("").to_dict(orient='records')
                response_data["dataframe"] = df_dict
                response_data["columns"] = result['dataframe'].columns.tolist()
                response_data["rows"] = len(result['dataframe'])
                response_data["preview"] = df_dict[:10]  # First 10 rows for preview

            elif response_data['has_text_content']:
                response_data["text_content"] = result['text_content'][:5000]  # First chunk

            return response_data
        else:
            return {
                "success": False,
                "filename": uploaded_file.filename,
                "error": result['error']
            }

    except Exception as e:
        return {
            "success": False,
            "filename": uploaded_file.filename,
            "error": f"Processing error: {str(e)}"
        }

# ==================== File Conversion Routes ====================

@app.post("/process-files")
async def process_files(files: list[UploadFile] = File(...)):
    """Process uploaded files and extract structured data"""
    results = {}

    for uploaded_file in files:
        # Process each file using the conversion module
        file_result = await process_uploaded_file(uploaded_file)
        results[uploaded_file.filename] = file_result

    return JSONResponse(content=results)

# New: download endpoint to create CSV/Excel from JSON dataframe
@app.post("/download")
async def download_dataframe(payload: dict = Body(...)):
    """
    payload: {
        "dataframe": [ {row}, ... ],
        "format": "csv" or "excel",
        "filename": "optional_name"
    }
    """
    try:
        df_records = payload.get("dataframe", [])
        fmt = payload.get("format", "csv").lower()
        filename = payload.get("filename", "extracted_table")

        if not isinstance(df_records, list):
            raise HTTPException(status_code=400, detail="dataframe must be a list of records")

        df = pd.DataFrame(df_records)

        output = io.BytesIO()
        if fmt == "csv":
            df.to_csv(output, index=False)
            output.seek(0)
            media_type = "text/csv"
            out_name = f"{filename}.csv"
        elif fmt in ("excel", "xlsx"):
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Extracted")
            output.seek(0)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            out_name = f"{filename}.xlsx"
        else:
            raise HTTPException(status_code=400, detail="format must be 'csv' or 'excel'")

        return StreamingResponse(output, media_type=media_type,
                                 headers={"Content-Disposition": f"attachment; filename={out_name}"})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Data Cleaner Routes ====================

@app.post("/api/analyze")
async def analyze_data(file: UploadFile = File(...)):
    """Analyze data quality issues in uploaded file"""
    try:
        # Read file based on extension
        if file.filename.endswith(".csv"):
            try:
                # Force engine='python' to avoid C-level buffer overflows
                df = pd.read_csv(file.file, sep=None, engine='python', on_bad_lines='skip')
                if len(df.columns) <= 1:
                    file.file.seek(0)
                    df = pd.read_csv(file.file, engine='python', on_bad_lines='skip')
            except Exception:
                file.file.seek(0)
                df = pd.read_csv(file.file, engine='python', encoding='ISO-8859-1', on_bad_lines='skip')
        else:
            file.file.seek(0)
            df = pd.read_excel(file.file)

        issues = detect_issues(df)
        response_data = {
            "success": True,
            "basic_info": {
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist(),
                "preview": df.head(5).to_dict(orient="records")
            },
            "issues": issues,
            "message": f"Analyzed {len(df)} rows and {len(df.columns)} columns"
        }
        return safe_json(response_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error analyzing file: {str(e)}")

@app.post("/api/clean")
async def clean_uploaded_data(file: UploadFile = File(...)):
    """Clean and download as Excel file"""
    try:
        # Read file based on extension
        if file.filename.endswith(".csv"):
            df = pd.read_csv(file.file)
        else:
            file.file.seek(0)  # Reset file pointer for Excel reading
            df = pd.read_excel(file.file)

        cleaned_df = clean_data(df)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            cleaned_df.to_excel(writer, index=False, sheet_name='CleanedData')
        output.seek(0)

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=cleaned_{file.filename.split('.')[0]}.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error cleaning file: {str(e)}")

@app.post("/api/clean-and-analyze")
async def clean_and_analyze(file: UploadFile = File(...)):
    """Analyze both original and cleaned data and return both previews"""
    print(f"DEBUG: /api/clean-and-analyze called for {file.filename}")
    try:
        # Read file based on extension
        if file.filename.endswith(".csv"):
            try:
                df = pd.read_csv(file.file, sep=None, engine='python', on_bad_lines='skip')
                if len(df.columns) <= 1:
                    file.file.seek(0)
                    df = pd.read_csv(file.file, engine='python', on_bad_lines='skip')
            except Exception:
                file.file.seek(0)
                df = pd.read_csv(file.file, engine='python', encoding='ISO-8859-1', on_bad_lines='skip')
        else:
            file.file.seek(0)
            df = pd.read_excel(file.file)

        print(f"DEBUG: Data loaded, cleaning and analyzing...")
        original_issues = detect_issues(df)

        cleaned_df = clean_data(df)
        cleaned_issues = detect_issues(cleaned_df)
        print(f"DEBUG: Clean & Analyze complete. Improvement: {len(original_issues) - len(cleaned_issues)}")

        response = {
            "success": True,
            "original_analysis": {
                "rows": len(df),
                "columns": len(df.columns),
                "issues": original_issues,
                "preview": df.head(5).to_dict(orient="records")
            },
            "cleaned_analysis": {
                "rows": len(cleaned_df),
                "columns": len(cleaned_df.columns),
                "issues": cleaned_issues,
                "preview": cleaned_df.head(10).to_dict(orient="records")
            },
            "improvement": len(original_issues) - len(cleaned_issues)
        }

        return safe_json(response)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

# ==================== Dashboard Routes ====================

from backend.dashboard_agent import DashboardAgent

# Initialize Dashboard Agent
dashboard_agent = DashboardAgent()

@app.post("/api/dashboard/start")
async def start_dashboard(file: UploadFile = File(...)):
    """Convert/Clean file and generate initial dashboard"""
    print(f"DEBUG: /api/dashboard/start called for {file.filename}")
    try:
        # 1. Load file
        file_content = await file.read()
        file_wrapper = io.BytesIO(file_content)
        
        if file.filename.endswith(".csv"):
            print(f"DEBUG: Reading CSV with robust Python engine...")
            try:
                # Use engine='python' to avoid C-buffer overflow on large EEG data
                df = pd.read_csv(io.BytesIO(file_content), sep=None, engine='python', on_bad_lines='skip')
                
                if len(df.columns) <= 1:
                    # Retry with default comma if auto-detect failed
                    df = pd.read_csv(io.BytesIO(file_content), engine='python', on_bad_lines='skip')
            except Exception as e:
                print(f"DEBUG: Standard read failed ({e}), trying ISO-8859-1 fallback...")
                df = pd.read_csv(io.BytesIO(file_content), engine='python', encoding='ISO-8859-1', on_bad_lines='skip')
        else:
            df = pd.read_excel(file_wrapper)

        original_size = len(df)
        print(f"DEBUG: File loaded ({original_size} rows, {len(df.columns)} columns)")

        # NOTE: No row sampling — the visualization engine uses aggregations
        # that are efficient on full datasets regardless of size.
        
        if len(df.columns) > 100:
            print(f"DEBUG: Reducing column count from {len(df.columns)} to 100 for better performance")
            # Prioritize numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            other_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
            keep_cols = (other_cols[:20] + numeric_cols[:80])[:100]
            df = df[keep_cols]

        # 2. Clean data (reuse existing cleaner)
        print(f"DEBUG: Cleaning data...")
        df = clean_data(df)
        
        # 3. Start Dashboard Session
        print(f"DEBUG: DF Types:\n{df.dtypes}")
        session_id, charts, kpis, columns, slicers, pages = dashboard_agent.start_session(df)
        print(f"DEBUG: Dashboard started. session_id={session_id}, slicers={len(slicers)}")
        
        # 4. Final safety check on all JSON outputs
        response_payload = {
            "success": True,
            "session_id": session_id,
            "charts": charts,
            "kpis": kpis,
            "columns": columns,
            "slicers": slicers,
            "pages": pages,
            "message": "Dashboard initialized"
        }
        return safe_json(response_payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error starting dashboard: {str(e)}")

@app.post("/api/dashboard/chat")
async def dashboard_chat(payload: dict = Body(...)):
    """
    payload: { "session_id": "...", "message": "...", "language": "Hindi" }
    """
    session_id = payload.get("session_id")
    message = payload.get("message")
    language = payload.get("language", "English")
    
    if not session_id or not message:
        print("DEBUG: Chat request missing session_id or message")
        raise HTTPException(status_code=400, detail="Missing session_id or message")
        
    print(f"DEBUG: Chat request for session {session_id} in language {language}: {message}")
    result = dashboard_agent.process_prompt(session_id, message, language=language)
    
    if result is None or result.get("charts") is None:
        print(f"DEBUG: Session {session_id} not found or failed")
        raise HTTPException(status_code=404, detail="Session not found or invalid")
        
    return result

@app.get("/api/dashboard/{session_id}")
async def get_dashboard_state(session_id: str):
    session = dashboard_agent.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    active_idx = session.get("active_page_idx", 0)
    active_page = session["pages"][active_idx]
    
    return {
        "success": True,
        "charts": active_page["charts"],
        "kpis": active_page.get("kpis", []),
        "slicers": session.get("slicers", []),
        "pages": session.get("pages", []),
        "theme": session.get("theme", "light"),
        "active_page_idx": active_idx,
        "history": session["history"]
    }

# ==================== Insight Generation Routes ====================

from backend.insight_agent import insight_agent
from backend.data_insights import generate_data_insights

# Directory for saved visualizations
SAVED_VIZ_DIR = os.path.join(os.path.dirname(__file__), "saved_visualizations")
os.makedirs(SAVED_VIZ_DIR, exist_ok=True)


@app.post("/api/insights/generate")
async def generate_insights(file: UploadFile = File(...), language: str = Form(default="English")):
    """Generate AI-powered insights from images, PDFs, Excel, CSV, or DOCX. Supports multilingual output."""
    try:
        content_type = file.content_type or ""
        filename = file.filename or "unknown"

        # Determine file category
        image_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp']
        pdf_types = ['application/pdf']
        data_types = [
            'text/csv', 'application/csv',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        ]
        doc_types = [
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/msword',
        ]

        file_bytes = await file.read()

        # Route to appropriate analyzer
        if content_type in image_types or content_type in pdf_types:
            insights = insight_agent.analyze_dashboard_image(
                file_bytes=file_bytes,
                mime_type=content_type,
                filename=filename,
                language=language
            )
        elif content_type in data_types or filename.lower().endswith(('.csv', '.xlsx', '.xls')):
            insights = insight_agent.analyze_data_file(
                file_bytes=file_bytes,
                mime_type=content_type,
                filename=filename,
                language=language
            )
        elif content_type in doc_types or filename.lower().endswith(('.docx', '.doc')):
            # For docs, use the file converter to extract text, then treat as image-style analysis
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as tmp:
                    tmp.write(file_bytes)
                    temp_path = tmp.name
                result = converter.process_file(temp_path)
                if result['success'] and result.get('text_content'):
                    # Use Gemini to analyze the text content (with model cascade)
                    from backend.gemini_helpers import get_gemini_client, call_gemini
                    client = get_gemini_client()
                    if client:
                        prompt = f"""## MANDATORY LANGUAGE RULE — READ THIS FIRST
You MUST write the ENTIRE output in **{language}**. Every word of every field MUST be in **{language}**.
Do NOT write in English. Do NOT mix languages. If you output even one English sentence, you have FAILED.

Analyze this document text and provide 4-6 actionable business insights.
You are "Vidhur" — a senior business advisor. Use simple language, give practical advice, and be encouraging.

Each insight must have: title, description, why_it_matters, action_steps (ALL MUST be in {language}).

Document text:
{result['text_content'][:5000]}

Reply with ONLY a JSON array in {language}: [{{"title": "...", "description": "...", "why_it_matters": "...", "action_steps": "..."}}]

## FINAL CHECK: Verify ZERO English words in output. Language: {language}."""
                        text = call_gemini(prompt, client=client)
                        insights = json.loads(text.strip())
                    else:
                        insights = [{"title": "Document Loaded", "description": f"Extracted text from '{filename}'. Gemini API is needed for deeper analysis."}]
                else:
                    insights = [{"title": "No Content Found", "description": f"Could not extract readable content from '{filename}'."}]
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {content_type}. Supported: images, PDF, Excel, CSV, DOCX."
            )

        return {"success": True, "insights": insights}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating insights: {str(e)}")


@app.post("/api/visualizations/save")
async def save_visualization(
    file: UploadFile = File(...),
    email: str = Form(...),
    title: str = Form(default="Dashboard Snapshot"),
    session_id: str = Form(default=""),
):
    """Save a dashboard visualization screenshot for a user."""
    try:
        user_dir = os.path.join(SAVED_VIZ_DIR, email.replace("@", "_at_").replace(".", "_"))
        os.makedirs(user_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = re.sub(r'[^a-zA-Z0-9_\- ]', '', title).strip().replace(' ', '_')[:50]
        filename = f"{safe_title}_{timestamp}.png"
        filepath = os.path.join(user_dir, filename)

        file_bytes = await file.read()
        with open(filepath, "wb") as f:
            f.write(file_bytes)

        # Save metadata
        meta_path = os.path.join(user_dir, f"{safe_title}_{timestamp}.json")
        metadata = {
            "title": title,
            "filename": filename,
            "session_id": session_id,
            "saved_at": datetime.now().isoformat(),
            "size_bytes": len(file_bytes),
        }
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return {"success": True, "message": "Visualization saved!", "filename": filename}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving visualization: {str(e)}")


@app.get("/api/visualizations/list")
async def list_visualizations(email: str = Query(...)):
    """List saved visualizations for a user."""
    try:
        user_dir = os.path.join(SAVED_VIZ_DIR, email.replace("@", "_at_").replace(".", "_"))

        if not os.path.exists(user_dir):
            return {"success": True, "visualizations": []}

        visualizations = []
        meta_files = sorted(glob.glob(os.path.join(user_dir, "*.json")), reverse=True)

        for meta_path in meta_files[:20]:  # limit to 20 most recent
            try:
                with open(meta_path, "r") as f:
                    meta = json.load(f)

                img_path = os.path.join(user_dir, meta["filename"])
                if os.path.exists(img_path):
                    # Create base64 thumbnail
                    with open(img_path, "rb") as img_f:
                        img_bytes = img_f.read()
                    thumbnail = base64.b64encode(img_bytes).decode("utf-8")

                    visualizations.append({
                        "title": meta.get("title", "Untitled"),
                        "filename": meta["filename"],
                        "saved_at": meta.get("saved_at", ""),
                        "thumbnail": f"data:image/png;base64,{thumbnail}",
                    })
            except Exception as e:
                print(f"Error reading visualization metadata: {e}")
                continue

        return {"success": True, "visualizations": visualizations}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing visualizations: {str(e)}")


@app.post("/api/visualizations/insights")
async def insights_from_saved(payload: dict = Body(...)):
    """Generate insights from a previously saved visualization."""
    try:
        email = payload.get("email", "")
        filename = payload.get("filename", "")

        if not email or not filename:
            raise HTTPException(status_code=400, detail="Missing email or filename")

        user_dir = os.path.join(SAVED_VIZ_DIR, email.replace("@", "_at_").replace(".", "_"))
        filepath = os.path.join(user_dir, filename)

        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Saved visualization not found")

        with open(filepath, "rb") as f:
            file_bytes = f.read()

        language = payload.get("language", "English")

        insights = insight_agent.analyze_dashboard_image(
            file_bytes=file_bytes,
            mime_type="image/png",
            filename=filename,
            language=language
        )

        return {"success": True, "insights": insights}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating insights: {str(e)}")


@app.post("/api/dashboard/insights/{session_id}")
async def get_dashboard_insights(session_id: str, payload: dict = Body(default={})):
    """Generate insights from dashboard session data. Accepts optional { language: 'Hindi' }."""
    language = payload.get("language", "English") if payload else "English"
    print(f"DEBUG: /api/dashboard/insights/ triggered for session: {session_id}, language: {language}")
    try:
        session = dashboard_agent.get_session(session_id)
        if not session:
            print(f"DEBUG: Insight Request Failed - Session {session_id} not found in memory (Backend likely restarted)")
            raise HTTPException(status_code=404, detail="Dashboard session not found. Please re-upload your file.")
        
        df = session["df"]
        active_idx = session.get("active_page_idx", 0)
        charts = session["pages"][active_idx]["charts"]
        
        print(f"DEBUG: Generating insights for dataset ({len(df)} rows, {len(df.columns)} columns) in {language}...")
        insights = generate_data_insights(df, charts, language=language)
        print(f"DEBUG: Insights generation successful. {len(insights)} items found.")
        
        return safe_json({
            "success": True,
            "insights": insights
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: CRITICAL ERROR in insight generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error analyzing dashboard: {str(e)}")

# ==================== Common Routes ====================

@app.get("/")
async def root():
    return {"message": "AutoDash AI Full Stack API is running! 🚀"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "AutoDash AI Full Stack API"}

# ==================== API Documentation ====================

@app.get("/endpoints")
async def list_endpoints():
    """List all available endpoints"""
    endpoints = {
        "file_conversion": {
            "POST /process-files": "Process uploaded files (PDF, DOCX, images, Excel, CSV) and extract structured data",
            "POST /download": "Create and download CSV/XLSX from JSON dataframe"
        },
        "data_cleaning": {
            "POST /api/analyze": "Analyze data quality issues in uploaded file",
            "POST /api/clean": "Clean data and download as Excel file",
            "POST /api/clean-and-analyze": "Analyze both original and cleaned data"
        },
        "info": {
            "GET /": "API root message",
            "GET /health": "Health check",
            "GET /endpoints": "This endpoints list"
        }
    }
    return endpoints

# ==================== Command Line Functionality ====================
# (Keep your existing CLI; unchanged except server port default)
def command_line_main():
    """Command line interface for file processing"""
    parser = argparse.ArgumentParser(description="AI-Powered Dynamic Table Extractor")
    parser.add_argument("--input", "-i", required=True, help="Input file or directory path")
    parser.add_argument("--output", "-o", help="Output directory path")
    parser.add_argument("--format", "-f", choices=['csv', 'excel'], default='csv',
                       help="Output format (csv or excel)")
    parser.add_argument("--tesseract", "-t", help="Path to Tesseract executable")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--clean", "-c", action="store_true", help="Clean data after extraction")

    args = parser.parse_args()

    # Initialize converter with Tesseract path if provided
    global converter
    if args.tesseract:
        converter = FileConverter(tesseract_path=args.tesseract)

    # Determine if input is file or directory
    input_paths = []
    if os.path.isfile(args.input):
        input_paths = [args.input]
    elif os.path.isdir(args.input):
        input_paths = [os.path.join(args.input, f) for f in os.listdir(args.input)
                      if os.path.isfile(os.path.join(args.input, f))]
    else:
        print(f"Error: Input path '{args.input}' does not exist")
        return

    # Set output directory
    output_dir = args.output or os.getcwd()
    os.makedirs(output_dir, exist_ok=True)

    # Process files
    results = []

    for file_path in input_paths:
        if args.verbose:
            print(f"Processing: {file_path}")

        result = converter.process_file(file_path)
        file_name = os.path.basename(file_path)

        if result['success']:
            if result['dataframe'] is not None and not result['dataframe'].empty:
                df = result['dataframe']

                # Apply data cleaning if requested
                if args.clean:
                    df = clean_data(df)
                    clean_suffix = "_cleaned"
                else:
                    clean_suffix = "_structured"

                # Save structured data
                base_name = os.path.splitext(file_name)[0]
                output_file = os.path.join(output_dir, f"{base_name}{clean_suffix}.{args.format}")

                try:
                    converter.save_dataframe(df, output_file, args.format)

                    if args.verbose:
                        print(f"  ✅ Extracted {len(df)} rows, {len(df.columns)} columns")
                        print(f"  📊 Columns: {', '.join(df.columns.tolist())}")
                        if args.clean:
                            print(f"  🧹 Data cleaning applied")
                        print(f"  💾 Saved to: {output_file}")

                    results.append({
                        'file': file_name,
                        'status': 'success',
                        'type': 'structured_data',
                        'cleaned': args.clean,
                        'rows': len(df),
                        'columns': len(df.columns),
                        'output_file': output_file
                    })

                except Exception as e:
                    print(f"  ❌ Error saving {file_name}: {e}")
                    results.append({
                        'file': file_name,
                        'status': 'error',
                        'error': str(e)
                    })

            elif result['text_content']:
                # Save extracted text
                base_name = os.path.splitext(file_name)[0]
                output_file = os.path.join(output_dir, f"{base_name}_extracted.txt")

                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(result['text_content'])

                if args.verbose:
                    print(f"  ℹ️  No structured data found, extracted text saved")
                    print(f"  💾 Saved to: {output_file}")

                results.append({
                    'file': file_name,
                    'status': 'success',
                    'type': 'text_only',
                    'output_file': output_file
                })
            else:
                print(f"  ⚠️  No data extracted from {file_name}")
                results.append({
                    'file': file_name,
                    'status': 'no_data',
                    'error': 'No structured data or text content found'
                })
        else:
            print(f"  ❌ Error processing {file_name}: {result['error']}")
            results.append({
                'file': file_name,
                'status': 'error',
                'error': result['error']
            })

    # Print summary
    print("\n" + "="*50)
    print("PROCESSING SUMMARY")
    print("="*50)

    success_count = len([r for r in results if r['status'] == 'success'])
    error_count = len([r for r in results if r['status'] == 'error'])
    no_data_count = len([r for r in results if r['status'] == 'no_data'])

    print(f"Total files processed: {len(results)}")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Errors: {error_count}")
    print(f"⚠️  No data: {no_data_count}")

    # Save results summary
    summary_file = os.path.join(output_dir, "processing_summary.json")
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n📊 Detailed results saved to: {summary_file}")

def interactive_mode():
    """Interactive mode for testing individual files"""
    print("🧠 AI-Powered Dynamic Table Extractor - Interactive Mode")
    print("Type 'quit' to exit\n")

    while True:
        file_path = input("Enter file path: ").strip()

        if file_path.lower() in ['quit', 'exit', 'q']:
            break

        if not os.path.exists(file_path):
            print("❌ File not found. Please try again.\n")
            continue

        print(f"\nProcessing: {file_path}")

        # Get file info
        info = converter.get_file_info(file_path)

        if info['success']:
            if info['has_structured_data']:
                print(f"✅ Structured data found:")
                print(f"   Rows: {info['rows']}")
                print(f"   Columns: {info['columns']}")
                print(f"   Columns: {', '.join(info['column_names'])}")

                # Show preview
                result = converter.process_file(file_path)
                print(f"\n📋 Data preview:")
                print(result['dataframe'].head().to_string())

                # Ask if user wants to clean data
                clean_choice = input("\n🧹 Clean data before saving? (y/n) [n]: ").lower().strip() or 'n'
                df_to_save = result['dataframe']
                if clean_choice == 'y':
                    df_to_save = clean_data(df_to_save)
                    print("✅ Data cleaning applied")

                # Ask if user wants to save
                save = input("\n💾 Save to file? (y/n): ").lower().strip()
                if save == 'y':
                    format_choice = input("Format (csv/excel) [csv]: ").lower().strip() or 'csv'
                    output_path = input(f"Output path [output.{format_choice}]: ").strip()
                    if not output_path:
                        output_path = f"output.{format_choice}"

                    try:
                        converter.save_dataframe(df_to_save, output_path, format_choice)
                        print(f"✅ Saved to: {output_path}")
                    except Exception as e:
                        print(f"❌ Error saving: {e}")

            elif info['has_text_content']:
                print("ℹ️  Text content extracted (no structured data found)")
                result = converter.process_file(file_path)
                print(f"\n📝 Text preview (first 500 chars):")
                print(result['text_content'][:500] + "..." if len(result['text_content']) > 500 else result['text_content'])
            else:
                print("⚠️  No data extracted from file")
        else:
            print(f"❌ Error: {info['error']}")

        print("\n" + "-"*50 + "\n")

# ==================== Main Execution ====================

if __name__ == "__main__":
    import sys

    # Check if running as FastAPI server or command line tool
    if len(sys.argv) > 1 and not any(arg in sys.argv for arg in ['--input', '-i', '--help', '-h']):
        # Run as FastAPI server
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        # Run as command line tool
        if len(sys.argv) > 1:
            # Command line mode
            command_line_main()
        else:
            # Interactive mode
            interactive_mode()
