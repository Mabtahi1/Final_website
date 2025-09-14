"""
Business Intelligence Analyzer Module
Integrates with main Flask app
"""
import boto3
import json
import textract
import tempfile
import os
import logging
import hashlib
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class BusinessAnalyzer:
    def __init__(self):
        self._response_cache = {}
        
    def analyze_question(self, question, custom_keywords=""):
        """Analyze a business question and return structured insights"""
        try:
            if not question or not question.strip():
                return {"error": "Question cannot be empty", "keywords": [], "insights": {}}

            analysis_id = hashlib.md5(f"{question}_{custom_keywords}".encode()).hexdigest()[:8]
            prompt = self._get_business_prompt(question, custom_keywords)
            
            response = self._call_claude(prompt)
            if response.startswith("Error:"):
                return {"error": response, "keywords": [], "insights": {}}

            parsed_result = self._parse_response(response)
            return {
                "keywords": parsed_result.get("keywords", []),
                "insights": parsed_result.get("structured_insights", {}),
                "analysis_id": analysis_id,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error in analyze_question: {str(e)}")
            return {"error": f"Analysis failed: {str(e)}", "keywords": [], "insights": {}}

    def analyze_text(self, text, question=None, keywords=None):
        """Analyze text content with optional focus"""
        try:
            if not text:
                return {"error": "Text content is required"}
            
            analysis_question = question or "Analyze this content for business insights"
            prompt = self._get_content_prompt(analysis_question, keywords or "", text[:2000])
            
            response = self._call_claude(prompt)
            if response.startswith("Error:"):
                return {"error": response}
                
            parsed_result = self._parse_response(response)
            return {
                "keywords": parsed_result.get("keywords", []),
                "insights": parsed_result.get("structured_insights", {}),
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error in analyze_text: {str(e)}")
            return {"error": f"Text analysis failed: {str(e)}"}

    def analyze_url(self, url, question=None, keywords=None):
        """Analyze web content from URL"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.extract()
            
            text = soup.get_text()
            text = ' '.join(text.split())[:2000]
            
            return self.analyze_text(text, question, keywords)
            
        except Exception as e:
            logger.error(f"Error analyzing URL: {str(e)}")
            return {"error": f"URL analysis failed: {str(e)}"}

    def analyze_file(self, file_content, filename, question=None, keywords=None):
        """Analyze uploaded file content"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name

            text = textract.process(tmp_path).decode("utf-8")
            os.unlink(tmp_path)
            
            return self.analyze_text(text, question, keywords)
            
        except Exception as e:
            logger.error(f"Error analyzing file: {str(e)}")
            return {"error": f"File analysis failed: {str(e)}"}

    def _call_claude(self, prompt):
        """Call AWS Bedrock Claude API"""
        try:
            prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
            if prompt_hash in self._response_cache:
                return self._response_cache[prompt_hash]

            bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
            
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2500,
                "temperature": 0.3,
                "top_k": 150,
                "top_p": 0.9,
            }

            response = bedrock.invoke_model(
                modelId="anthropic.claude-3-sonnet-20240229-v1:0",
                contentType="application/json",
                accept="application/json",
                body=json.dumps(payload),
            )

            result = json.loads(response["body"].read())
            response_text = result["content"][0]["text"]
            self._response_cache[prompt_hash] = response_text
            return response_text

        except Exception as e:
            logger.error(f"Error calling Claude: {str(e)}")
            return f"Error calling Claude: {str(e)}"

    def _get_business_prompt(self, question, custom_keywords=""):
        """Generate business analysis prompt"""
        return f"""You are a senior business strategist. Analyze this question and provide strategic insights.

Question: {question}
Keywords: {custom_keywords}

Respond using EXACTLY this format:

**KEYWORDS IDENTIFIED:**
[List exactly 5 business keywords separated by commas]

**STRATEGIC ANALYSIS:**

**KEYWORD 1: [First Keyword]**
**INSIGHTS:**
1. Market Opportunity: [Analysis of market opportunity]
2. Implementation Strategy: [How to implement]
3. Success Metrics: [How to measure success]
**ACTIONS:**
1. [Detailed actionable insight 150-200 words with specific strategies, metrics, and timelines]
2. [Detailed actionable insight 150-200 words with implementation steps and ROI expectations]
3. [Detailed actionable insight 150-200 words with risk mitigation and success measures]

[Continue for 5 keywords total]

Include specific numbers, percentages, dollar amounts, and timeframes in every action item."""

    def _get_content_prompt(self, question, keywords, content):
        """Generate content analysis prompt"""
        return f"""Analyze the provided content and deliver strategic business insights.

Question: {question}
Keywords: {keywords}
Content: {content}

Use the same format as the business analysis with 5 keywords and detailed actions."""

    def _parse_response(self, response):
        """Parse Claude response into structured format"""
        try:
            lines = response.strip().split("\n")
            keywords = []
            structured_insights = {}
            current_keyword = None
            mode = None
            current_titles = []
            current_insights = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if line.startswith("**KEYWORDS IDENTIFIED:**"):
                    mode = "keywords"
                    continue

                elif mode == "keywords" and not line.startswith("**"):
                    keyword_line = line.replace("[", "").replace("]", "")
                    keywords = [k.strip() for k in keyword_line.split(",") if k.strip()]
                    mode = None
                    continue

                elif line.startswith("**KEYWORD") and ":" in line:
                    if current_keyword and (current_titles or current_insights):
                        structured_insights[current_keyword] = {
                            "titles": current_titles,
                            "insights": current_insights
                        }
                    
                    keyword_part = line.split(":", 1)[1].strip()
                    current_keyword = keyword_part.replace("**", "").strip()
                    current_titles = []
                    current_insights = []
                    continue

                elif line.startswith("**INSIGHTS:**"):
                    mode = "titles"
                    continue

                elif line.startswith("**ACTIONS:**"):
                    mode = "insights"
                    continue

                elif mode == "titles" and current_keyword:
                    if line and (line[0].isdigit() or line.startswith("- ")):
                        content = line.split(".", 1)[1].strip() if line[0].isdigit() else line[2:].strip()
                        if content:
                            current_titles.append(content)

                elif mode == "insights" and current_keyword:
                    if line and (line[0].isdigit() or line.startswith("- ")):
                        content = line.split(".", 1)[1].strip() if line[0].isdigit() else line[2:].strip()
                        if content:
                            current_insights.append(content)
                    elif current_insights and not line.startswith("**"):
                        current_insights[-1] += " " + line.strip()

            if current_keyword and (current_titles or current_insights):
                structured_insights[current_keyword] = {
                    "titles": current_titles,
                    "insights": current_insights
                }

            return {"keywords": keywords, "structured_insights": structured_insights}

        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
            return {"keywords": [], "structured_insights": {}}
