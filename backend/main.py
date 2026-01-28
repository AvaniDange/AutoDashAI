import os
import argparse
import json
import uvicorn
import pandas as pd
import io
from typing import List
from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.encoders import jsonable_encoder

from file_conversion import FileConverter
from data_cleaner import detect_issues, clean_data, safe_json  # keep your existing cleaner

# Initialize the file converter
converter = FileConverter()

# ==================== FastAPI App ====================
app = FastAPI(title="AutoDash AI Full Stack API")

# Allow frontend CORS access
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict this later for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Helper Functions ====================
async def process_uploaded_file(uploaded_file: UploadFile):
    """Process uploaded file and return structured data"""
    try:
        # Save uploaded file temporarily
        file_content = await uploaded_file.read()
        temp_path = f"temp_{uploaded_file.filename}"
        with open(temp_path, "wb") as f:
            f.write(file_content)

        # Process the file
        result = converter.process_file(temp_path)

        # Clean up temporary file
        try:
            os.remove(temp_path)
        except Exception:
            pass

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
            df = pd.read_csv(file.file)
        else:
            file.file.seek(0)  # Reset file pointer for Excel reading
            df = pd.read_excel(file.file)

        df = safe_json(df)
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
        return JSONResponse(content=jsonable_encoder(response_data))
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
    try:
        # Read file based on extension
        if file.filename.endswith(".csv"):
            df = pd.read_csv(file.file)
        else:
            file.file.seek(0)  # Reset file pointer for Excel reading
            df = pd.read_excel(file.file)

        df = safe_json(df)
        original_issues = detect_issues(df)

        cleaned_df = clean_data(df)
        cleaned_df = safe_json(cleaned_df)
        cleaned_issues = detect_issues(cleaned_df)

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

        return JSONResponse(content=jsonable_encoder(response))

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

# ==================== Dashboard Routes ====================

from dashboard_agent import DashboardAgent

# Initialize Dashboard Agent
dashboard_agent = DashboardAgent()

@app.post("/api/dashboard/start")
async def start_dashboard(file: UploadFile = File(...)):
    """Convert/Clean file and generate initial dashboard"""
    try:
        # 1. Save and load file
        file_content = await file.read()
        file_wrapper = io.BytesIO(file_content)
        
        if file.filename.endswith(".csv"):
            df = pd.read_csv(file_wrapper)
        else:
            df = pd.read_excel(file_wrapper)

        # 2. Clean data (reuse existing cleaner)
        df = clean_data(df)
        df = safe_json(df)
        
        # 3. Start Dashboard Session
        session_id, charts, kpis, columns = dashboard_agent.start_session(df)
        
        return {
            "success": True,
            "session_id": session_id,
            "charts": charts,
            "kpis": kpis,
            "columns": columns,
            "message": "Dashboard initialized"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error starting dashboard: {str(e)}")

@app.post("/api/dashboard/chat")
async def dashboard_chat(payload: dict = Body(...)):
    """
    payload: { "session_id": "...", "message": "..." }
    """
    session_id = payload.get("session_id")
    message = payload.get("message")
    
    if not session_id or not message:
        raise HTTPException(status_code=400, detail="Missing session_id or message")
        
    charts, reply = dashboard_agent.process_prompt(session_id, message)
    
    if charts is None:
        raise HTTPException(status_code=404, detail="Session not found")
        
    return {
        "success": True,
        "charts": charts,
        "reply": reply
    }

@app.get("/api/dashboard/{session_id}")
async def get_dashboard_state(session_id: str):
    session = dashboard_agent.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    return {
        "success": True,
        "charts": session["charts"],
        "history": session["history"]
    }

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
        uvicorn.run(app, host="0.0.0.0", port=8003)
    else:
        # Run as command line tool
        if len(sys.argv) > 1:
            # Command line mode
            command_line_main()
        else:
            # Interactive mode
            interactive_mode()
