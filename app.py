"""
Prolexis Analytics - Integrated Flask Application
Now includes BI Analyzer and Legal Doc Management
"""
from datetime import datetime
from flask import Flask, render_template, request, redirect, jsonify, session, send_file, flash
import os
import stripe
import pyrebase
from werkzeug.utils import secure_filename
import io

# Import our custom modules
from bi_analyzer import BusinessAnalyzer
from legal_doc_manager import LegalDocManager

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Stripe configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')

# Firebase configuration
firebase_config = {
    "apiKey": "AIzaSyDt6y7YRFVF_zrMTYPn4z4ViHjLbmfMsLQ",
    "authDomain": "trend-summarizer-6f28e.firebaseapp.com",
    "projectId": "trend-summarizer-6f28e",
    "storageBucket": "trend-summarizer-6f28e.firebasestorage.app",
    "messagingSenderId": "655575726457",
    "databaseURL": "https://trend-summarizer-6f28e-default-rtdb.firebaseio.com",
    "appId": "1:655575726457:web:9ae1d0d363c804edc9d7a8",
    "measurementId": "G-HHY482GQKZ"
}

firebase = pyrebase.initialize_app(firebase_config)
db = firebase.database()
auth = firebase.auth()

# Initialize our modules
bi_analyzer = BusinessAnalyzer()
legal_manager = LegalDocManager()

# Utility functions
def get_user_info(email):
    """Get user subscription info from Firebase"""
    try:
        user_key = email.replace(".", "_")
        user_data = db.child("users").child(user_key).get().val()
        return user_data
    except:
        return None

def check_usage_limits(email, action_type="summary"):
    """Check if user can perform action based on their plan"""
    user_info = get_user_info(email)
    if not user_info:
        return False, "No subscription found"
    
    usage_limits = user_info.get('usage_limits', {})
    current_usage = user_info.get('current_usage', {})
    
    if action_type == "summary":
        limit = usage_limits.get('summaries_per_month', 0)
        current = current_usage.get('summaries_this_month', 0)
        if limit != "unlimited" and current >= limit:
            return False, f"Monthly limit of {limit} analyses reached"
    
    return True, "Access granted"

def is_logged_in():
    """Check if user is logged in"""
    return 'user_email' in session

def login_required(f):
    """Decorator to require login"""
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            return redirect('/signin')
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Original website routes
@app.route('/')
@app.route('/index')
def hello():
    return render_template('index.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/signin')
def signin():
    return render_template('signin.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/tools')
def tools():
    if not is_logged_in():
        return redirect('/signin')
    
    user_info = get_user_info(session['user_email'])
    return render_template('tools.html', user_info=user_info)

# Authentication routes
@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        # Firebase authentication would go here
        # For now, simple validation
        if email and password:
            session['user_email'] = email
            user_info = get_user_info(email)
            return jsonify({'success': True, 'user_info': user_info})
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True})

# BI Analyzer routes
@app.route('/bi-analyzer')
@login_required
def bi_analyzer_page():
    user_info = get_user_info(session['user_email'])
    return render_template('bi_analyzer.html', user_info=user_info)

@app.route('/api/bi/analyze-question', methods=['POST'])
@login_required
def analyze_question():
    try:
        user_email = session['user_email']
        can_use, message = check_usage_limits(user_email, "summary")
        
        if not can_use:
            return jsonify({'error': message, 'upgrade_required': True}), 429
        
        data = request.get_json()
        question = data.get('question')
        keywords = data.get('keywords', '')
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        result = bi_analyzer.analyze_question(question, keywords)
        
        if not result.get('error'):
            # Increment usage count here
            pass
            
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bi/analyze-text', methods=['POST'])
@login_required
def analyze_text():
    try:
        user_email = session['user_email']
        can_use, message = check_usage_limits(user_email, "summary")
        
        if not can_use:
            return jsonify({'error': message, 'upgrade_required': True}), 429
        
        data = request.get_json()
        text = data.get('text')
        question = data.get('question', '')
        keywords = data.get('keywords', '')
        
        if not text:
            return jsonify({'error': 'Text content is required'}), 400
        
        result = bi_analyzer.analyze_text(text, question, keywords)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bi/analyze-url', methods=['POST'])
@login_required
def analyze_url():
    try:
        user_email = session['user_email']
        can_use, message = check_usage_limits(user_email, "summary")
        
        if not can_use:
            return jsonify({'error': message, 'upgrade_required': True}), 429
        
        data = request.get_json()
        url = data.get('url')
        question = data.get('question', '')
        keywords = data.get('keywords', '')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        result = bi_analyzer.analyze_url(url, question, keywords)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bi/analyze-file', methods=['POST'])
@login_required
def analyze_file():
    try:
        user_email = session['user_email']
        can_use, message = check_usage_limits(user_email, "summary")
        
        if not can_use:
            return jsonify({'error': message, 'upgrade_required': True}), 429
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        question = request.form.get('question', '')
        keywords = request.form.get('keywords', '')
        
        file_content = file.read()
        result = bi_analyzer.analyze_file(file_content, file.filename, question, keywords)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Legal Document Management routes
@app.route('/legal-docs')
@login_required
def legal_docs_page():
    user_info = get_user_info(session['user_email'])
    return render_template('legal_docs.html', user_info=user_info)

@app.route('/api/legal/documents')
@login_required
def get_documents():
    try:
        user_email = session['user_email']
        client_filter = request.args.get('client')
        type_filter = request.args.get('type')
        search_term = request.args.get('search')
        
        result = legal_manager.get_documents(user_email, client_filter, type_filter, search_term)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/legal/upload', methods=['POST'])
@login_required
def upload_document():
    try:
        user_email = session['user_email']
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        client_name = request.form.get('client')
        matter_description = request.form.get('matter')
        
        if not client_name or not matter_description:
            return jsonify({'error': 'Client and matter description are required'}), 400
        
        result = legal_manager.upload_document(file, client_name, matter_description, user_email)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/legal/download/<document_id>')
@login_required
def download_document(document_id):
    try:
        result = legal_manager.get_document_content(document_id)
        
        if result.get('error'):
            return jsonify(result), 404
        
        return send_file(
            io.BytesIO(result['content']),
            as_attachment=True,
            download_name=result['filename'],
            mimetype=result['mime_type']
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/legal/delete/<document_id>', methods=['DELETE'])
@login_required
def delete_document(document_id):
    try:
        user_email = session['user_email']
        result = legal_manager.delete_document(document_id, user_email)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/legal/clients')
@login_required
def get_clients():
    try:
        user_email = session['user_email']
        result = legal_manager.get_client_list(user_email)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/legal/clients', methods=['POST'])
@login_required
def add_client():
    try:
        user_email = session['user_email']
        data = request.get_json()
        
        client_name = data.get('name')
        client_type = data.get('type')
        
        result = legal_manager.add_client(client_name, client_type, user_email)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/legal/time-entries')
@login_required
def get_time_entries():
    try:
        user_email = session['user_email']
        client_filter = request.args.get('client')
        
        result = legal_manager.get_time_entries(user_email, client_filter)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/legal/time-entries', methods=['POST'])
@login_required
def add_time_entry():
    try:
        user_email = session['user_email']
        data = request.get_json()
        
        result = legal_manager.add_time_entry(data, user_email)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/legal/analytics')
@login_required
def get_analytics():
    try:
        user_email = session['user_email']
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        result = legal_manager.get_analytics(user_email, start_date, end_date)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Payment routes (existing)
@app.route('/payment/<plan_type>')
def payment(plan_type):
    plans = {
        'basic': {'price': 1000, 'name': 'Basic Plan', 'description': '5 summaries/month'},
        'pro': {'price': 4900, 'name': 'Pro Plan', 'description': 'Unlimited summaries + competitor tracking'},
        'onetime': {'price': 2500, 'name': 'One-time Plan', 'description': 'PDF from up to 3 sources'},
        'starter': {'price': 49900, 'name': 'Starter Plan', 'description': 'Dashboard + Data cleanup'},
        'premium': {'price': 99900, 'name': 'Premium Plan', 'description': 'Automation + Forecasting + $100/mo'}
    }
    
    if plan_type not in plans:
        return "Invalid plan", 400
    
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': plans[plan_type]['name'],
                        'description': plans[plan_type]['description'],
                    },
                    'unit_amount': plans[plan_type]['price'],
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'https://prolexisanalytics.com/payment-success?session_id={{CHECKOUT_SESSION_ID}}&plan={plan_type}',
            cancel_url='https://prolexisanalytics.com/',
            metadata={'plan_type': plan_type},
            customer_email=request.args.get('email'),
            billing_address_collection='required'
        )
        return redirect(session.url)
    except Exception as e:
        return f"Error creating payment session: {str(e)}", 400

@app.route('/payment-success')
def payment_success():
    session_id = request.args.get('session_id')
    plan_type = request.args.get('plan')
    
    if not session_id:
        return "Missing session ID", 400
    
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.payment_status == 'paid':
            customer_email = session.customer_details.email if session.customer_details else None
            
            payment_info = {
                'email': customer_email,
                'plan': plan_type,
                'amount': session.amount_total,
                'session_id': session_id,
                'timestamp': datetime.now().isoformat()
            }
            
            return render_template('payment_success.html', 
                                 plan=plan_type, 
                                 session_id=session_id,
                                 email=customer_email)
        else:
            return "Payment not completed", 400
            
    except Exception as e:
        return f"Error verifying payment: {str(e)}", 400

@app.route('/health')
def health():
    return {'status': 'healthy', 'service': 'Prolexis Analytics Platform'}

def update_user_subscription(email, plan_type):
    """Update user subscription in Firebase"""
    user_key = email.replace(".", "_")
    
    plans = {
        "basic": {
            "summaries_per_month": 5,
            "sources_limit": 3,
            "has_competitor_tracking": False,
            "has_automation": False,
            "has_forecasting": False
        },
        "pro": {
            "summaries_per_month": "unlimited",
            "sources_limit": "unlimited", 
            "has_competitor_tracking": True,
            "has_automation": False,
            "has_forecasting": False
        },
        "onetime": {
            "summaries_per_month": 3,
            "sources_limit": 3,
            "has_competitor_tracking": False,
            "has_automation": False,
            "has_forecasting": False
        },
        "starter": {
            "summaries_per_month": 10,
            "sources_limit": 5,
            "has_competitor_tracking": False,
            "has_automation": True,
            "has_forecasting": False
        },
        "premium": {
            "summaries_per_month": "unlimited",
            "sources_limit": "unlimited",
            "has_competitor_tracking": True,
            "has_automation": True,
            "has_forecasting": True
        }
    }
    
    update_data = {
        "subscription_type": plan_type,
        "subscription_status": "active",
        "payment_date": datetime.now().isoformat(),
        "usage_limits": plans.get(plan_type, plans["basic"]),
        "current_usage": {
            "summaries_this_month": 0,
            "last_reset_date": datetime.now().replace(day=1).isoformat()
        }
    }
    
    db.child("users").child(user_key).update(update_data)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
