import sys
import traceback

try:
    print("Testing gemini_helpers...")
    from backend.gemini_helpers import get_gemini_client, call_gemini, call_gemini_fast, call_gemini_json, call_gemini_multimodal, compute_data_hash
    print("  OK: gemini_helpers")
    
    print("Testing visualization_engine...")
    from backend.visualization_engine import VisualizationEngine, profile_columns
    print("  OK: visualization_engine")
    
    print("Testing data_cleaner...")
    from backend.data_cleaner import detect_issues, clean_data, safe_json
    print("  OK: data_cleaner")
    
    print("Testing data_insights...")
    from backend.data_insights import generate_data_insights
    print("  OK: data_insights")
    
    print("Testing insight_agent...")
    from backend.insight_agent import insight_agent
    print("  OK: insight_agent")
    
    print("Testing dashboard_agent...")
    from backend.dashboard_agent import DashboardAgent
    print("  OK: dashboard_agent")
    
    print("Testing main app import...")
    from backend.main import app
    print("  OK: main")
    
    print("\n=== ALL IMPORTS PASSED ===")
except Exception as e:
    print(f"\nFAILED: {e}")
    traceback.print_exc()
    sys.exit(1)
