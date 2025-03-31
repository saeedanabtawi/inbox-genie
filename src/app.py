import os
import csv
import io
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user, LoginManager
import secrets

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not found, using default environment variables")

# Import models and authentication utilities
from .models import db, User
from .auth import init_auth, auth_bp

# Initialize Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///inbox_genie.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize authentication
app = init_auth(app)

# Register the authentication blueprint
app.register_blueprint(auth_bp, url_prefix='/auth')

# Setup global login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class EmailGenerator:
    @staticmethod
    def generate_email(recipient_data):
        """
        Generate a personalized cold email based on recipient data
        
        Args:
            recipient_data (dict): Dictionary containing recipient information
            
        Returns:
            str: Personalized email content
        """
        # Extract recipient data
        name = recipient_data.get('name', 'Prospect')
        role = recipient_data.get('role', 'Professional')
        company = recipient_data.get('company', 'Company')
        industry = recipient_data.get('industry', 'your industry')
        recent_activity = recipient_data.get('recent_activity', '')
        industry_news = recipient_data.get('industry_news', '')
        pain_points = recipient_data.get('pain_points', '')
        
        # Generate a personalized opening based on available information
        if recent_activity:
            opening = f"I recently came across your {recent_activity} and was impressed by your work at {company}."
        elif industry_news:
            opening = f"I noticed the recent news about {industry_news} in the {industry} sector and thought of {company}."
        else:
            opening = f"I hope this email finds you well. I noticed your role as {role} at {company} and thought I'd reach out."
        
        # Generate a value proposition based on pain points
        if pain_points:
            value_prop = f"Many {role}s in {industry} face challenges with {pain_points}. Our solution has helped similar companies increase efficiency by 30% and reduce costs significantly."
        else:
            value_prop = f"Our solution has helped many companies in {industry} increase efficiency by 30% and reduce costs significantly."
        
        # Construct the full email
        email = f"""Subject: Quick Question About {company}'s Approach to Growth

Hi {name},

{opening}

{value_prop}

I'd love to share how we've helped other {industry} companies achieve similar results. Would you be open to a brief 15-minute call next week to explore if there might be a fit?

Looking forward to your response,

{current_user.username if current_user.is_authenticated else '[Your Name]'}
[Your Position]
[Your Company]
[Your Contact Information]"""
        
        return email
    
    @staticmethod
    def process_csv_data(csv_data):
        """Process CSV data and generate emails for each recipient
        
        Args:
            csv_data (str): CSV data as a string
            
        Returns:
            dict: Dictionary containing generated emails and validation results
        """
        result = {
            'success': True,
            'emails': [],
            'errors': [],
            'total_recipients': 0,
            'successful_recipients': 0
        }
        
        try:
            # Parse CSV data
            csv_file = io.StringIO(csv_data)
            csv_reader = csv.DictReader(csv_file)
            
            # Get headers from CSV
            headers = csv_reader.fieldnames
            
            # Validate required fields
            required_fields = ['name', 'role', 'company']
            missing_fields = [field for field in required_fields if field.lower() not in [h.lower() for h in headers]]
            
            if missing_fields:
                result['success'] = False
                result['errors'].append(f"Missing required columns: {', '.join(missing_fields)}")
                return result
            
            # Process each row
            for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 to account for header row
                result['total_recipients'] += 1
                
                # Normalize header names to lowercase and create a standardized row dictionary
                standardized_row = {}
                for header in headers:
                    key = header.lower().strip()
                    standardized_row[key] = row[header].strip() if row[header] else ''
                
                # Validate required fields in each row
                row_errors = []
                for field in required_fields:
                    if not standardized_row.get(field):
                        row_errors.append(f"Missing {field}")
                        
                if row_errors:
                    result['errors'].append(f"Row {row_num}: {', '.join(row_errors)}")
                    continue
                
                try:
                    # Generate email for this recipient
                    email = EmailGenerator.generate_email(standardized_row)
                    result['emails'].append({
                        'recipient': standardized_row,
                        'email': email
                    })
                    result['successful_recipients'] += 1
                except Exception as e:
                    result['errors'].append(f"Row {row_num}: Error generating email - {str(e)}")
            
            # Update success flag if we have any emails
            if result['successful_recipients'] == 0 and result['total_recipients'] > 0:
                result['success'] = False
                
            return result
            
        except Exception as e:
            result['success'] = False
            result['errors'].append(f"Error processing CSV: {str(e)}")
            return result

@app.route('/')
def landing():
    """Render the landing page - public access"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

# Add a home alias for backward compatibility
@app.route('/home')
def home():
    """Alias for landing page to maintain backward compatibility"""
    return landing()

@app.route('/dashboard')
@login_required
def dashboard():
    """Render the dashboard page - requires login"""
    return render_template('index.html')

@app.route('/generate-email', methods=['POST'])
@login_required
def email_generator():
    """API endpoint to generate a personalized email - requires login"""
    data = request.json
    
    # Generate the email
    email_content = EmailGenerator.generate_email(data)
    
    return jsonify({'email': email_content})

@app.route('/about')
def about():
    """Render the about page - public access"""
    return render_template('about.html')

@app.route('/bulk')
@login_required
def bulk_emails():
    """Render the bulk email page - requires login"""
    return render_template('bulk.html')

@app.route('/process-bulk-emails', methods=['POST'])
@login_required
def process_bulk_emails():
    """API endpoint to process bulk emails - requires login"""
    data = request.json
    csv_data = data.get('csv_data', '')
    
    # Process CSV and generate emails
    result = EmailGenerator.process_csv_data(csv_data)
    return jsonify(result)

@app.route('/profile')
@login_required
def profile():
    """Render the user profile page - requires login"""
    return render_template('profile.html')

@app.route('/auth/login')
def login_page():
    """Redirect to auth login route"""
    return redirect(url_for('auth.login'))

@app.route('/auth/register')
def register_page():
    """Redirect to auth register route"""
    return redirect(url_for('auth.register'))

# Create error templates directory if it doesn't exist
@app.before_first_request
def create_error_templates():
    """Create error templates directory"""
    templates_dir = os.path.join(app.root_path, 'templates')
    errors_dir = os.path.join(templates_dir, 'errors')
    os.makedirs(errors_dir, exist_ok=True)
    
    # Create 404 page if it doesn't exist
    error_404_path = os.path.join(errors_dir, '404.html')
    if not os.path.exists(error_404_path):
        with open(error_404_path, 'w') as f:
            f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>404 - Page Not Found</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="/static/css/styles.css">
</head>
<body>
    <div class="container text-center py-5">
        <h1 class="display-1">404</h1>
        <p class="lead">Page not found</p>
        <p>The page you're looking for doesn't exist.</p>
        <a href="/" class="btn btn-primary">Go Home</a>
    </div>
</body>
</html>""")
    
    # Create 500 page if it doesn't exist
    error_500_path = os.path.join(errors_dir, '500.html')
    if not os.path.exists(error_500_path):
        with open(error_500_path, 'w') as f:
            f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>500 - Server Error</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="/static/css/styles.css">
</head>
<body>
    <div class="container text-center py-5">
        <h1 class="display-1">500</h1>
        <p class="lead">Server Error</p>
        <p>Something went wrong on our end. Please try again later.</p>
        <a href="/" class="btn btn-primary">Go Home</a>
    </div>
</body>
</html>""")

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)
