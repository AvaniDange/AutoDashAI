"""
Insight Agent - Analyzes dashboard images using local OCR and pattern recognition.
No API keys required - works 100% offline!
"""
import io
import re
from typing import List, Dict
from PIL import Image

# Try to import OCR library
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("Warning: pytesseract not installed. Install it for better OCR-based insights.")

class InsightAgent:
    def __init__(self):
        print("Insight Agent: Local mode initialized (no API required)")

    def analyze_dashboard_image(self, file_bytes: bytes, mime_type: str, filename: str) -> List[Dict[str, str]]:
        """
        Analyze a dashboard image using local OCR and pattern recognition.
        """
        try:
            # Open image
            image = Image.open(io.BytesIO(file_bytes))
            
            # Try OCR if available
            extracted_text = ""
            if OCR_AVAILABLE:
                try:
                    extracted_text = pytesseract.image_to_string(image)
                except Exception as e:
                    print(f"OCR failed: {e}")
                    extracted_text = ""
            
            # Analyze the extracted text
            insights = self._analyze_text(extracted_text, filename)
            
            return insights
            
        except Exception as e:
            print(f"Image analysis error: {e}")
            return self._generic_insights()

    def _analyze_text(self, text: str, filename: str) -> List[Dict[str, str]]:
        """Analyze extracted text to generate insights."""
        insights = []
        text_lower = text.lower()
        
        # Look for numbers (potential metrics)
        numbers = re.findall(r'\d+(?:,\d{3})*(?:\.\d+)?', text)
        percentages = re.findall(r'\d+(?:\.\d+)?%', text)
        
        # Pattern: Revenue/Sales
        if 'revenue' in text_lower or 'sales' in text_lower:
            if percentages:
                insights.append({
                    "title": "Revenue Performance",
                    "description": f"The dashboard shows revenue metrics with changes around {percentages[0] if percentages else 'significant percentage'}. Monitor these trends for business growth opportunities."
                })
            else:
                insights.append({
                    "title": "Sales Metrics Detected",
                    "description": "Revenue and sales data is displayed. Consider tracking month-over-month changes to identify growth patterns."
                })
        
        # Pattern: Customer/User metrics
        if 'customer' in text_lower or 'user' in text_lower:
            insights.append({
                "title": "Customer Engagement",
                "description": "Customer or user metrics are present. Focus on retention rates and customer lifetime value to optimize business strategy."
            })
        
        # Pattern: Growth/Decline indicators
        if any(word in text_lower for word in ['increase', 'growth', 'up', 'rise']):
            insights.append({
                "title": "Positive Trend Identified",
                "description": "The dashboard indicates upward trends. Analyze the contributing factors and replicate successful strategies."
            })
        elif any(word in text_lower for word in ['decrease', 'decline', 'down', 'drop']):
            insights.append({
                "title": "Performance Alert",
                "description": "Declining metrics detected. Investigate root causes and implement corrective actions promptly."
            })
        
        # Pattern: Time-based data
        if any(word in text_lower for word in ['month', 'quarter', 'year', 'daily', 'weekly']):
            insights.append({
                "title": "Time-Series Analysis",
                "description": "The dashboard includes temporal data. Use this to forecast future trends and plan resource allocation accordingly."
            })
        
        # Pattern: Multiple categories/segments
        category_keywords = ['category', 'segment', 'region', 'product', 'department']
        if any(word in text_lower for word in category_keywords):
            insights.append({
                "title": "Multi-Dimensional View",
                "description": "Data is segmented by categories or regions. Compare performance across segments to identify top performers and areas needing improvement."
            })
        
        # Add numerical insights if we found numbers
        if len(numbers) >= 3:
            insights.append({
                "title": "Key Metrics Overview",
                "description": f"The dashboard displays {len(numbers)} numerical indicators. Establish KPI benchmarks to track performance against business objectives."
            })
        
        # If we didn't find specific patterns, provide generic but useful insights
        if not insights:
            insights = self._generic_insights()
        
        # Limit to 6 insights max
        return insights[:6]

    def _generic_insights(self) -> List[Dict[str, str]]:
        """Return generic but useful insights when specific analysis isn't possible."""
        return [
            {
                "title": "Visual Data Representation",
                "description": "The dashboard uses visual elements to communicate data. Ensure charts are clearly labeled and color-coded for easy interpretation."
            },
            {
                "title": "Key Performance Indicators",
                "description": "Identify the most critical KPIs shown and set up alerts for significant changes to enable proactive decision-making."
            },
            {
                "title": "Data Freshness",
                "description": "Verify that the dashboard data is updated regularly. Real-time or near-real-time data enables faster response to business changes."
            },
            {
                "title": "Actionable Metrics",
                "description": "Focus on metrics that directly inform business decisions. Avoid vanity metrics that don't drive meaningful action."
            },
            {
                "title": "Comparative Analysis",
                "description": "Compare current performance against historical data and industry benchmarks to contextualize your metrics."
            },
            {
                "title": "Drill-Down Capability",
                "description": "When anomalies are detected, drill down into the underlying data to understand root causes and take targeted action."
            }
        ]


# Global instance
insight_agent = InsightAgent()
