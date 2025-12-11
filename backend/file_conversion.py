import pandas as pd
import pdfplumber
from docx import Document
from PIL import Image
import pytesseract
import io
import re
from typing import Union, Dict, List, Optional
import os

class FileConverter:
    def __init__(self, tesseract_path: str = None):
        """
        Initialize FileConverter with optional Tesseract path
        """
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
    
    def extract_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text
        except Exception as e:
            raise Exception(f"PDF extraction error: {e}")
    
    def extract_docx(self, file_path: str) -> str:
        """Extract text from Word document"""
        try:
            doc = Document(file_path)
            return "\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            raise Exception(f"DOCX extraction error: {e}")
    
    def extract_excel_csv(self, file_path: str) -> pd.DataFrame:
        """Extract data from Excel or CSV file"""
        try:
            if file_path.lower().endswith(".csv"):
                return pd.read_csv(file_path)
            else:
                return pd.read_excel(file_path)
        except Exception as e:
            raise Exception(f"Excel/CSV extraction error: {e}")
    
    def extract_image_text(self, file_path: str) -> str:
        """Extract text from image using OCR"""
        try:
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img)
            return text
        except Exception as e:
            raise Exception(f"Image OCR extraction error: {e}")
    
    def parse_text_to_table(self, text: str) -> pd.DataFrame:
        """Parse text and extract structured table data from descriptive text"""
        try:
            # Clean the text
            text = re.sub(r'\s+', ' ', text).strip()
            
            # Try multiple parsing strategies
            
            # Strategy 1: Look for country-based expenditure data
            df1 = self._parse_country_expenditure(text)
            if not df1.empty:
                return df1
                
            # Strategy 2: Look for company revenue data (original logic)
            df2 = self._parse_company_revenue(text)
            if not df2.empty:
                return df2
                
            # Strategy 3: Generic number and entity extraction
            df3 = self._parse_generic_entities(text)
            if not df3.empty:
                return df3
                
            return pd.DataFrame()
            
        except Exception as e:
            print(f"Parsing error: {e}")
            return pd.DataFrame()
    
    def _parse_country_expenditure(self, text: str) -> pd.DataFrame:
        """Parse country expenditure data like the IELTS example"""
        # Look for country names
        countries = re.findall(r'\b(United States|USA|US|Japan|United Kingdom|UK|India|Brazil|China|Germany|France|Canada|Australia)\b', text, re.IGNORECASE)
        
        if not countries:
            return pd.DataFrame()
            
        # Look for expenditure categories
        categories = re.findall(r'\b(food|housing|transportation|education|entertainment|healthcare|utilities)\b', text, re.IGNORECASE)
        
        # Extract monetary values with context
        money_pattern = r'(\$?[0-9]+(?:\,[0-9]{3})*(?:\.[0-9]+)?)\s*(?:million|billion|thousand|k|M|B)?\s*(?:dollars|USD)?'
        money_matches = re.findall(money_pattern, text)
        
        # More sophisticated parsing for the IELTS example
        rows = []
        
        # Pattern for "spends $X on category" or "allocate $X for category"
        spend_patterns = [
            r'spends?\s+(?:around|about|approximately)?\s*\$?([0-9,]+(?:\.[0-9]+)?)\s+on\s+(\w+)',
            r'allocate\s+(?:only)?\s*\$?([0-9,]+(?:\.[0-9]+)?)\s+for\s+(\w+)',
            r'spend\s+of\s+\$?([0-9,]+(?:\.[0-9]+)?)\s+on\s+(\w+)',
            r'(\w+).*?\$?([0-9,]+(?:\.[0-9]+))',
        ]
        
        for pattern in spend_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) >= 2:
                    amount = match.group(1).replace(',', '')
                    category = match.group(2).lower()
                    
                    # Try to associate with countries
                    for country in countries:
                        # Check if country appears near this match
                        start_pos = max(0, match.start() - 200)
                        end_pos = min(len(text), match.end() + 200)
                        context = text[start_pos:end_pos]
                        
                        if country.lower() in context.lower():
                            row = {
                                'Country': country,
                                'Category': category.title(),
                                'Amount': float(amount),
                                'Currency': 'USD'
                            }
                            # Avoid duplicates
                            if not any(r['Country'] == row['Country'] and r['Category'] == row['Category'] for r in rows):
                                rows.append(row)
        
        # Alternative pattern for comparative data
        comp_pattern = r'(\w+(?:\s+\w+)?)\s+(?:spends|allocates)\s+\$?([0-9,]+)'
        comp_matches = re.finditer(comp_pattern, text, re.IGNORECASE)
        for match in comp_matches:
            if len(match.groups()) == 2:
                country_candidate = match.group(1)
                amount = match.group(2).replace(',', '')
                
                # Check if this looks like a country
                if any(c.lower() in country_candidate.lower() for c in ['States', 'Japan', 'UK', 'India', 'Brazil']):
                    row = {
                        'Country': country_candidate,
                        'Category': 'General',
                        'Amount': float(amount),
                        'Currency': 'USD'
                    }
                    if not any(r['Country'] == row['Country'] for r in rows):
                        rows.append(row)
        
        if rows:
            return pd.DataFrame(rows)
        return pd.DataFrame()
    
    def _parse_company_revenue(self, text: str) -> pd.DataFrame:
        """Parse company revenue data (original logic)"""
        # Find all companies (capitalized words ending with Ltd or similar)
        companies = list(set(re.findall(r'\b([A-Z][a-zA-Z]+(?:\s+Ltd|Ltd|Inc|Corp|Corporation))\b', text)))
        # Find all years
        years = list(set(map(int, re.findall(r'(19\d{2}|20\d{2})', text))))
        years.sort()

        # Patterns for metrics
        metric_patterns = {
            'Revenue_$M': r'\$([0-9]+(?:\.[0-9]+)?)\s*M',
            'Revenue_$B': r'\$([0-9]+(?:\.[0-9]+)?)\s*B',
            'Female_Participation_%': r'(\d+)%\s*(?:of senior management|female|participation|positions)?',
            'ROA_%': r'ROA.*?(\d+)%', 
            'Net_Income_%': r'Net Income.*?(\d+)%',
            'Profit': r'profit.*?\$([0-9]+(?:\.[0-9]+)?)',
            'Expenditure': r'expenditure.*?\$([0-9]+(?:\.[0-9]+)?)'
        }

        # Prepare table rows
        rows = []
        for company in companies:
            for year in years:
                row = {'Company': company, 'Year': year}
                # For each metric, search text near company and year
                for col, pattern in metric_patterns.items():
                    regex = rf"{re.escape(company)}.*?{year}.*?{pattern}"
                    match = re.search(regex, text, flags=re.IGNORECASE|re.DOTALL)
                    if match:
                        row[col] = match.group(1)
                    else:
                        row[col] = ""
                # Only add row if we found at least one metric
                if any(str(row[col]) for col in metric_patterns.keys()):
                    rows.append(row)
        
        df = pd.DataFrame(rows)
        # Remove empty columns
        if not df.empty:
            df = df.loc[:, (df != "").any(axis=0)]
        return df
    
    def _parse_generic_entities(self, text: str) -> pd.DataFrame:
        """Generic parsing for entities and numbers"""
        # Extract all numbers with context
        number_pattern = r'(\$?[0-9]+(?:\,[0-9]{3})*(?:\.[0-9]+)?)\s*(?:million|billion|thousand|k|M|B)?'
        numbers = re.findall(number_pattern, text)
        
        # Extract potential entities (capitalized phrases)
        entities = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text)
        
        if numbers and entities:
            # Create a simple table with entities and numbers found
            rows = []
            for i, entity in enumerate(entities[:10]):  # Limit to first 10 entities
                if i < len(numbers):
                    rows.append({
                        'Entity': entity,
                        'Value': numbers[i].replace('$', '').replace(',', ''),
                        'Type': 'Numerical'
                    })
            
            if rows:
                return pd.DataFrame(rows)
        
        return pd.DataFrame()
    
    def process_file(self, file_path: str) -> Dict:
        """
        Process a single file and return structured data
        
        Returns:
            Dict with keys: 'success', 'dataframe', 'text_content', 'error'
        """
        try:
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'error': f"File not found: {file_path}",
                    'dataframe': None,
                    'text_content': None
                }
            
            df_final = None
            text_content = ""
            file_ext = file_path.lower()
            
            if file_ext.endswith(".pdf"):
                text_content = self.extract_pdf(file_path)
            elif file_ext.endswith(".docx"):
                text_content = self.extract_docx(file_path)
            elif file_ext.endswith((".png", ".jpg", ".jpeg")):
                text_content = self.extract_image_text(file_path)
            elif file_ext.endswith((".csv", ".xlsx")):
                df_final = self.extract_excel_csv(file_path)
            else:
                return {
                    'success': False,
                    'error': f"Unsupported file type: {file_path}",
                    'dataframe': None,
                    'text_content': None
                }
            
            # If we have text content but no dataframe, parse the text
            if df_final is None and text_content:
                print(f"Parsing text content: {len(text_content)} characters")
                df_final = self.parse_text_to_table(text_content)
                print(f"Parsing result: {len(df_final) if df_final is not None else 0} rows")
            
            return {
                'success': True,
                'dataframe': df_final,
                'text_content': text_content if df_final is None or df_final.empty else None,
                'error': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Error processing {file_path}: {e}",
                'dataframe': None,
                'text_content': None
            }
    
    def save_dataframe(self, df: pd.DataFrame, output_path: str, format: str = 'csv'):
        """
        Save dataframe to file
        
        Args:
            df: DataFrame to save
            output_path: Output file path
            format: 'csv' or 'excel'
        """
        try:
            if format.lower() == 'csv':
                df.to_csv(output_path, index=False)
            elif format.lower() in ['excel', 'xlsx']:
                df.to_excel(output_path, index=False)
            else:
                raise ValueError("Format must be 'csv' or 'excel'")
            return True
        except Exception as e:
            raise Exception(f"Error saving file: {e}")
    
    def get_file_info(self, file_path: str) -> Dict:
        """Get basic information about the processed file"""
        result = self.process_file(file_path)
        
        info = {
            'file_name': os.path.basename(file_path),
            'success': result['success'],
            'has_structured_data': result['dataframe'] is not None and not result['dataframe'].empty,
            'has_text_content': result['text_content'] is not None and result['text_content'] != "",
            'error': result['error']
        }
        
        if info['has_structured_data']:
            info['rows'] = len(result['dataframe'])
            info['columns'] = len(result['dataframe'].columns)
            info['column_names'] = list(result['dataframe'].columns)
        
        return info