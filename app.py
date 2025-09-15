from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <h1>Prolexis Analytics Platform</h1>
    <p>Application is running successfully!</p>
    <a href="/health">Health Check</a>
    '''

@app.route('/health')
def health():
    return {'status': 'healthy', 'service': 'Prolexis Analytics'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
