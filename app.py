from flask import Flask, render_template_string, request, jsonify, session
from bi_analyzer import BusinessAnalyzer
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Initialize BI analyzer
bi_analyzer = BusinessAnalyzer()

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Prolexis Analytics Platform</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; }
            .nav { margin-bottom: 30px; }
            .nav a { margin-right: 20px; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }
            .nav a:hover { background: #0056b3; }
            .section { margin-bottom: 30px; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Prolexis Analytics Platform</h1>
            <p>Advanced AI-powered business analysis and legal document management</p>
            
            <div class="nav">
                <a href="/">Home</a>
                <a href="/bi-analyzer">BI Analyzer</a>
                <a href="/health">Health Check</a>
            </div>
            
            <div class="section">
                <h2>Business Intelligence Analyzer</h2>
                <p>Analyze business questions, documents, and content for strategic insights.</p>
                <a href="/bi-analyzer">Launch BI Analyzer</a>
            </div>
            
            <div class="section">
                <h2>Legal Document Management</h2>
                <p>Coming soon - Manage legal documents and track time.</p>
            </div>
            
            <div class="section">
                <h2>System Status</h2>
                <p>Application is running successfully on AWS ECS Fargate!</p>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/bi-analyzer')
def bi_analyzer_page():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>BI Analyzer - Prolexis Analytics</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 900px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
            button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
            button:hover { background: #0056b3; }
            .results { margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 5px; }
            .keyword { display: inline-block; margin: 5px; padding: 5px 10px; background: #007bff; color: white; border-radius: 3px; }
            .insight { margin: 15px 0; padding: 15px; background: white; border-radius: 5px; border-left: 4px solid #007bff; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Business Intelligence Analyzer</h1>
            <a href="/">← Back to Home</a>
            
            <div class="form-group">
                <label for="question">Business Question:</label>
                <textarea id="question" rows="4" placeholder="e.g., What are the key opportunities in sustainable packaging for 2024?"></textarea>
            </div>
            
            <div class="form-group">
                <label for="keywords">Keywords (optional):</label>
                <input type="text" id="keywords" placeholder="e.g., sustainability, innovation, market">
            </div>
            
            <button onclick="analyzeQuestion()">Analyze Question</button>
            
            <div id="results" class="results" style="display: none;">
                <h3>Analysis Results</h3>
                <div id="keywords-section"></div>
                <div id="insights-section"></div>
            </div>
        </div>
        
        <script>
        async function analyzeQuestion() {
            const question = document.getElementById('question').value;
            const keywords = document.getElementById('keywords').value;
            
            if (!question.trim()) {
                alert('Please enter a question to analyze');
                return;
            }
            
            try {
                const response = await fetch('/api/analyze-question', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        question: question,
                        keywords: keywords
                    })
                });
                
                const result = await response.json();
                
                if (result.error) {
                    alert('Error: ' + result.error);
                    return;
                }
                
                displayResults(result);
                
            } catch (error) {
                alert('Analysis failed: ' + error.message);
            }
        }
        
        function displayResults(result) {
            const resultsDiv = document.getElementById('results');
            const keywordsSection = document.getElementById('keywords-section');
            const insightsSection = document.getElementById('insights-section');
            
            // Display keywords
            keywordsSection.innerHTML = '<h4>Key Strategic Areas:</h4>';
            result.keywords.forEach(keyword => {
                keywordsSection.innerHTML += `<span class="keyword">${keyword}</span>`;
            });
            
            // Display insights
            insightsSection.innerHTML = '<h4>Strategic Insights:</h4>';
            Object.keys(result.insights).forEach(keyword => {
                const insight = result.insights[keyword];
                insightsSection.innerHTML += `
                    <div class="insight">
                        <h5>${keyword}</h5>
                        <p><strong>Focus Areas:</strong> ${insight.titles.join(', ')}</p>
                        <p>${insight.insights[0]}</p>
                    </div>
                `;
            });
            
            resultsDiv.style.display = 'block';
        }
        </script>
    </body>
    </html>
    '''

@app.route('/api/analyze-question', methods=['POST'])
def analyze_question():
    try:
        data = request.get_json()
        question = data.get('question')
        keywords = data.get('keywords', '')
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        result = bi_analyzer.analyze_question(question, keywords)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    return {'status': 'healthy', 'service': 'Prolexis Analytics Platform'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
