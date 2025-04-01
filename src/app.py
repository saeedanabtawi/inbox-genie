import os
import csv
import io
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user, LoginManager
import secrets
import datetime as dt
from datetime import datetime, timedelta
from sqlalchemy import func
from .email_service import EmailService

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not found, using default environment variables")

# Import models and authentication utilities
from .models import db, User, SMTPConfig, EmailHistory, EmailTemplate
from .auth import init_auth, auth_bp

# Initialize Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///inbox_genie.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize authentication
app = init_auth(app)

# The auth_bp is already registered in init_auth function
# No need to register it again here

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
    def generate_email(recipient_data, template_type='cold_email'):
        """
        Generate a personalized cold email based on recipient data
        
        Args:
            recipient_data (dict): Dictionary containing recipient information
            template_type (str): Type of email template to use
            
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
        email = recipient_data.get('email', '')
        
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
        if template_type == 'cold_email':
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
        elif template_type == 'follow_up':
            email = f"""Hi {name},

I wanted to follow up on my previous email regarding how we can help {company} with {pain_points}. Have you had a chance to consider my proposal?

I'm available to discuss how our solution has helped companies like yours improve their results by 30% on average.

Let me know if you have 15 minutes this week for a quick call.

Best regards,
{current_user.username if current_user.is_authenticated else '[Your Name]'}
[Your Position]
[Your Company]
[Your Contact Information]"""
        elif template_type == 'meeting_request':
            email = f"""Hi {name},

I'd like to schedule a brief 15-minute call to discuss how our solution can help {company} address {pain_points}.

Are you available next Tuesday or Wednesday afternoon?

Looking forward to connecting!

Best regards,
{current_user.username if current_user.is_authenticated else '[Your Name]'}
[Your Position]
[Your Company]
[Your Contact Information]"""
        else:
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
    def get_default_template(template_type='cold_email'):
        """
        Get the default email template
        
        Args:
            template_type (str): Type of email template to use
            
        Returns:
            str: Default email template
        """
        if template_type == 'cold_email':
            return """Subject: Quick Question About {{company}}'s Approach to Growth

Hi {{name}},

I hope this email finds you well. I noticed your role as {{role}} at {{company}} and thought I'd reach out.

Many {{role}}s in {{industry}} face challenges with {{pain_points}}. Our solution has helped similar companies increase efficiency by 30% and reduce costs significantly.

I'd love to share how we've helped other {{industry}} companies achieve similar results. Would you be open to a brief 15-minute call next week to explore if there might be a fit?

Looking forward to your response,

{{username}}
{{position}}
{{company}}
{{contact_info}}"""
        elif template_type == 'follow_up':
            return """Hi {{name}},

I wanted to follow up on my previous email regarding how we can help {{company}} with {{pain_points}}. Have you had a chance to consider my proposal?

I'm available to discuss how our solution has helped companies like yours improve their results by 30% on average.

Let me know if you have 15 minutes this week for a quick call.

Best regards,
{{username}}
{{position}}
{{company}}
{{contact_info}}"""
        elif template_type == 'meeting_request':
            return """Hi {{name}},

I'd like to schedule a brief 15-minute call to discuss how our solution can help {{company}} address {{pain_points}}.

Are you available next Tuesday or Wednesday afternoon?

Looking forward to connecting!

Best regards,
{{username}}
{{position}}
{{company}}
{{contact_info}}"""
        else:
            return """Subject: Quick Question About {{company}}'s Approach to Growth

Hi {{name}},

I hope this email finds you well. I noticed your role as {{role}} at {{company}} and thought I'd reach out.

Many {{role}}s in {{industry}} face challenges with {{pain_points}}. Our solution has helped similar companies increase efficiency by 30% and reduce costs significantly.

I'd love to share how we've helped other {{industry}} companies achieve similar results. Would you be open to a brief 15-minute call next week to explore if there might be a fit?

Looking forward to your response,

{{username}}
{{position}}
{{company}}
{{contact_info}}"""
    
    @staticmethod
    def generate_email_from_template(recipient_data, template_content):
        """
        Generate a personalized email from a template
        
        Args:
            recipient_data (dict): Dictionary containing recipient information
            template_content (str): Email template content
            
        Returns:
            str: Personalized email content
        """
        # Replace placeholders in the template
        email = template_content.replace('{{name}}', recipient_data.get('name', 'Prospect'))
        email = email.replace('{{company}}', recipient_data.get('company', 'Company'))
        email = email.replace('{{role}}', recipient_data.get('role', 'Professional'))
        email = email.replace('{{industry}}', recipient_data.get('industry', 'your industry'))
        email = email.replace('{{pain_points}}', recipient_data.get('pain_points', ''))
        email = email.replace('{{username}}', current_user.username if current_user.is_authenticated else '[Your Name]')
        email = email.replace('{{position}}', '[Your Position]')
        email = email.replace('{{company}}', '[Your Company]')
        email = email.replace('{{contact_info}}', '[Your Contact Information]')
        
        return email
    
    @staticmethod
    def process_csv_data(csv_data, template_type='cold_email'):
        """Process CSV data and generate emails for each recipient
        
        Args:
            csv_data (str): CSV data as a string
            template_type (str): Type of email template to use
            
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
            required_fields = ['name', 'role', 'company', 'email']
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
                    email = EmailGenerator.generate_email(standardized_row, template_type)
                    result['emails'].append({
                        'recipient': standardized_row,
                        'email': email
                    })
                    result['successful_recipients'] += 1
                except Exception as e:
                    failure_count += 1
                    error_message = str(e)
                    error_messages.append(f"Failed to send email to {recipient_email}: {error_message}")
                    
                    # Record the failed email
                    email_history = EmailHistory(
                        user_id=current_user.id,
                        smtp_config_id=smtp_config.id,
                        recipient=recipient_email,
                        subject=subject,
                        content=content,
                        status='failed',
                        error_message=error_message,
                        sent_at=datetime.now()
                    )
                    db.session.add(email_history)
        
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
    """Render the dashboard page with analytics data"""
    # Get real user metrics from the database
    
    try:
        # Count emails sent by the current user
        emails_count = EmailHistory.query.filter_by(user_id=current_user.id).count()
        
        # Count unique bulk campaigns
        campaigns_count = db.session.query(func.count(func.distinct(EmailHistory.campaign_name))).filter(
            EmailHistory.user_id == current_user.id,
            EmailHistory.campaign_name.isnot(None)
        ).scalar() or 0
        
        # For now, we'll use a default score since we don't have this attribute yet
        avg_score = 8.7
        
        # Calculate usage percentage based on subscription tier limits
        max_emails = 500  # Default for premium
        if current_user.subscription_tier == 'Free':
            max_emails = 1
        elif current_user.subscription_tier == 'Basic':
            max_emails = 100
        elif current_user.subscription_tier == 'Professional':
            max_emails = 1000
        elif current_user.subscription_tier == 'Enterprise':
            max_emails = float('inf')
        
        usage_percentage = min(round((emails_count / max_emails) * 100), 100) if max_emails > 0 else 0
    except Exception as e:
        print(f"Error calculating dashboard metrics: {str(e)}")
        # Fallback to default values if there's an error
        emails_count = 0
        campaigns_count = 0
        avg_score = 0
        usage_percentage = 0
    
    # Get campaign data (keeping the demo data for now)
    analytics = {
        'user_stats': {
            'emails_generated': emails_count,
            'bulk_campaigns': campaigns_count,
            'avg_score': avg_score,
            'usage_percentage': usage_percentage
        },
        'campaigns': [
            {
                'name': 'Q2 Outreach',
                'type': 'Cold Email',
                'emails_sent': 27,
                'date': 'Mar 30, 2025',
                'open_rate': 68,
                'click_rate': 32,
                'reply_rate': 18,
                'status': 'Active'
            },
            {
                'name': 'March Prospects',
                'type': 'Cold Email',
                'emails_sent': 42,
                'date': 'Mar 15, 2025',
                'open_rate': 76,
                'click_rate': 29,
                'reply_rate': 32,
                'status': 'Completed'
            },
            {
                'name': 'Industry Conference',
                'type': 'Meeting Request',
                'emails_sent': 15,
                'date': 'Mar 10, 2025',
                'open_rate': 87,
                'click_rate': 53,
                'reply_rate': 47,
                'status': 'Completed'
            },
            {
                'name': 'Q1 Follow-ups',
                'type': 'Follow-Up',
                'emails_sent': 31,
                'date': 'Feb 28, 2025',
                'open_rate': 72,
                'click_rate': 41,
                'reply_rate': 35,
                'status': 'Completed'
            }
        ],
        'recent_activity': [
            {
                'type': 'campaign',
                'title': 'Bulk Campaign Generated',
                'description': 'Generated 27 personalized emails for "Q2 Outreach" campaign',
                'time': '2 hours ago'
            },
            {
                'type': 'template',
                'title': 'Template Created',
                'description': 'Created new template "Custom Follow-up" for tech industry',
                'time': 'Yesterday'
            },
            {
                'type': 'campaign',
                'title': 'Campaign Completed',
                'description': '"March Prospects" campaign completed with 32% response rate',
                'time': '3 days ago'
            },
            {
                'type': 'settings',
                'title': 'Settings Updated',
                'description': 'Updated notification preferences and sender information',
                'time': '1 week ago'
            },
            {
                'type': 'campaign',
                'title': 'Bulk Campaign Generated',
                'description': 'Generated 15 personalized emails for "Industry Conference" campaign',
                'time': '1 week ago'
            }
        ]
    }
    
    return render_template('dashboard.html', analytics=analytics)

@app.route('/profile')
@login_required
def profile():
    """Render the user profile page"""
    # In a real application, you might fetch user statistics from a database
    
    stats = {
        'emails_generated': 0,
        'bulk_campaigns': 0,
        'avg_score': 'N/A'
    }
    return render_template('profile.html', stats=stats)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    """Handle profile update form submission"""
    if request.method == 'POST':
        # In a real app, you would validate and update the user profile
        flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile'))

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """Handle password change form submission"""
    if request.method == 'POST':
        # In a real app, you would validate passwords and update them
        flash('Password changed successfully!', 'success')
    return redirect(url_for('profile'))

@app.route('/bulk')
@login_required
def bulk():
    """Render the bulk email generation page"""
    # Get user's custom templates from database
    custom_templates = EmailTemplate.query.filter_by(user_id=current_user.id).all()
    
    # Get the user's smtp configs
    smtp_configs = SMTPConfig.query.filter_by(user_id=current_user.id).all()
    
    return render_template('bulk.html', custom_templates=custom_templates, smtp_configs=smtp_configs)

@app.route('/send-bulk-emails', methods=['POST'])
@login_required
def send_bulk_emails():
    """Send multiple emails using configured SMTP server"""
    try:
        if not current_user.is_authenticated:
            return jsonify({"success": False, "error": "Authentication required"}), 401

        data = request.json
        if not data or 'emails' not in data or not data['emails']:
            return jsonify({"success": False, "error": "No emails provided"}), 400
        
        # Check if the user has SMTP configuration
        smtp_config_id = data.get('smtp_config_id')
        if not smtp_config_id:
            return jsonify({"success": False, "error": "No SMTP configuration selected"}), 400
        
        smtp_config = SMTPConfig.query.filter_by(id=smtp_config_id, user_id=current_user.id).first()
        if not smtp_config:
            return jsonify({"success": False, "error": "Invalid SMTP configuration"}), 400
        
        # Check if the user has reached the email limit
        email_count = EmailHistory.query.filter_by(user_id=current_user.id, sent_at=func.date(func.now())).count()
        email_limit = current_user.get_monthly_email_limit()
        emails_to_send_count = len(data['emails'])
        
        if email_count + emails_to_send_count > email_limit and email_limit != float('inf'):
            return jsonify({
                "success": False, 
                "error": f"You have reached your daily email limit ({email_limit}). Please upgrade your subscription to send more emails."
            }), 403
        
        # Prepare SMTP configuration dict
        smtp_config_dict = {
            'server': smtp_config.server,
            'port': smtp_config.port,
            'username': smtp_config.username,
            'password': smtp_config.password,
            'use_tls': smtp_config.use_tls,
            'email': smtp_config.email,
            'name': smtp_config.display_name
        }
        
        # Debug information
        print(f"SMTP Config: {smtp_config_dict}")
        print(f"Emails to send: {len(data['emails'])}")
        
        # Process each email
        success_count = 0
        failure_count = 0
        error_messages = []
        
        for email_data in data['emails']:
            try:
                recipient_email = email_data.get('recipient')
                subject = email_data.get('subject', "No Subject")
                content = email_data.get('content')
                
                if not recipient_email or not content:
                    failure_count += 1
                    error_messages.append(f"Missing data for email to {recipient_email}")
                    continue
                    
                # Send the email using the static method
                success, message = EmailService.send_email(
                    recipient_email=recipient_email,
                    subject=subject,
                    html_content=content,
                    smtp_config=smtp_config_dict
                )
                
                print(f"Email send attempt to {recipient_email}: {success}, {message}")
                
                if not success:
                    raise Exception(message)
                
                # Record the email history
                email_history = EmailHistory(
                    user_id=current_user.id,
                    smtp_config_id=smtp_config.id,
                    recipient=recipient_email,
                    subject=subject,
                    content=content,
                    status='sent',
                    sent_at=datetime.now()
                )
                db.session.add(email_history)
                success_count += 1
                
            except Exception as e:
                failure_count += 1
                error_message = str(e)
                error_messages.append(f"Failed to send email to {recipient_email}: {error_message}")
                
                # Record the failed email
                email_history = EmailHistory(
                    user_id=current_user.id,
                    smtp_config_id=smtp_config.id,
                    recipient=recipient_email,
                    subject=subject,
                    content=content,
                    status='failed',
                    error_message=error_message,
                    sent_at=datetime.now()
                )
                db.session.add(email_history)
        
        # Commit all the email history records at once
        db.session.commit()
        
        return jsonify({
            "success": True,
            "sent": success_count,
            "failed": failure_count,
            "errors": error_messages if failure_count > 0 else None
        })
    except Exception as e:
        # Catch any unexpected errors and return as JSON
        print(f"Error in send_bulk_emails: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}",
            "sent": 0,
            "failed": 0
        }), 500

@app.route('/templates')
@login_required
def manage_templates():
    """Render the template management page"""
    # Get the default templates
    default_templates = {
        'cold_email': EmailGenerator.get_default_template('cold_email'),
        'follow_up': EmailGenerator.get_default_template('follow_up'),
        'meeting_request': EmailGenerator.get_default_template('meeting_request')
    }
    
    # Load user's custom templates from the database
    custom_templates = EmailTemplate.query.filter_by(user_id=current_user.id).all()
    
    return render_template(
        'template_management.html', 
        templates=default_templates,
        custom_templates=custom_templates
    )

@app.route('/save-template', methods=['POST'])
@login_required
def save_template():
    """Save a customized email template"""
    data = request.json
    template_type = data.get('template_type')
    template_content = data.get('template_content')
    
    if not template_type or not template_content:
        return jsonify({'success': False, 'message': 'Template type and content are required'})
    
    try:
        # Check if this user already has a customized version of this default template
        existing_template = EmailTemplate.query.filter_by(
            user_id=current_user.id, 
            template_type=template_type
        ).first()
        
        if existing_template:
            # Update existing template
            existing_template.content = template_content
            existing_template.updated_at = datetime.now()
            db.session.commit()
            message = f'Template "{template_type}" updated successfully'
        else:
            # Create new template based on default
            new_template = EmailTemplate(
                user_id=current_user.id,
                name=template_type.replace('_', ' ').title(),
                description=f'Customized {template_type.replace("_", " ")} template',
                content=template_content,
                template_type=template_type,
                required_fields='name,company,role,email'
            )
            db.session.add(new_template)
            db.session.commit()
            message = f'Template "{template_type}" customized successfully'
        
        return jsonify({'success': True, 'message': message})
    
    except Exception as e:
        db.session.rollback()
        print(f"Error saving template: {str(e)}")
        return jsonify({'success': False, 'message': f'Error saving template: {str(e)}'}), 500

@app.route('/save-custom-template', methods=['POST'])
@login_required
def save_custom_template():
    """Save a new custom template"""
    data = request.json
    template_name = data.get('template_name')
    template_content = data.get('template_content')
    template_description = data.get('template_description', '')
    required_fields = data.get('required_fields', 'name,company,role,email')
    
    # Validate inputs
    if not template_name or not template_content:
        return jsonify({'success': False, 'message': 'Template name and content are required'})
    
    try:
        # Check if a template with this name already exists for this user
        existing_template = EmailTemplate.query.filter_by(
            user_id=current_user.id, 
            name=template_name
        ).first()
        
        if existing_template:
            # Update existing template
            existing_template.content = template_content
            existing_template.description = template_description
            existing_template.required_fields = required_fields
            existing_template.updated_at = datetime.now()
            db.session.commit()
            return jsonify({
                'success': True, 
                'message': f'Template "{template_name}" updated successfully',
                'template_id': existing_template.id
            })
        else:
            # Create new template
            new_template = EmailTemplate(
                user_id=current_user.id,
                name=template_name,
                description=template_description,
                content=template_content,
                template_type='custom',
                required_fields=required_fields
            )
            db.session.add(new_template)
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'message': f'Custom template "{template_name}" created successfully',
                'template_id': new_template.id
            })
    
    except Exception as e:
        db.session.rollback()
        print(f"Error saving template: {str(e)}")
        return jsonify({'success': False, 'message': f'Error saving template: {str(e)}'}), 500

@app.route('/bulk')
@login_required
def bulk_emails_alias():
    """Alias for bulk_emails to maintain backward compatibility"""
    return redirect(url_for('bulk'))

@app.route('/generate-email', methods=['POST'])
@login_required
def email_generator():
    """API endpoint to generate a personalized email"""
    data = request.json
    
    # Check if a specific template was requested
    template_type = data.get('template', 'cold_email')
    
    # Generate the email using the selected template
    email_content = EmailGenerator.generate_email(recipient_data=data, template_type=template_type)
    
    return jsonify({'email': email_content})

@app.route('/get-templates')
@login_required
def get_templates():
    """API endpoint to get available email templates"""
    templates = {
        'cold_email': EmailGenerator.get_default_template('cold_email'),
        'follow_up': EmailGenerator.get_default_template('follow_up'),
        'meeting_request': EmailGenerator.get_default_template('meeting_request')
    }
    return jsonify({'templates': templates})

@app.route('/about')
def about():
    """Redirect the about page to landing page since content is merged"""
    return redirect(url_for('landing'))

@app.route('/api/process-bulk-emails', methods=['POST'])
@login_required
def process_bulk_emails():
    """API endpoint to process bulk emails"""
    data = request.json
    csv_data = data.get('csv_data')
    template_id = data.get('template_id')
    
    if not csv_data:
        return jsonify({
            'success': False,
            'errors': ['No CSV data provided']
        })
    
    if not template_id:
        return jsonify({
            'success': False,
            'errors': ['No template selected']
        })
    
    try:
        # Parse CSV data
        csv_io = io.StringIO(csv_data)
        csv_reader = csv.DictReader(csv_io)
        
        if not csv_reader.fieldnames:
            return jsonify({
                'success': False,
                'errors': ['Invalid CSV format. Please check that your CSV is formatted correctly.']
            })
        
        required_fields = ['name', 'company', 'role', 'email']
        
        # Get the selected template
        template_content = None
        
        if template_id.startswith('default_'):
            # Get default template
            template_type = template_id.replace('default_', '')
            template_content = EmailGenerator.get_default_template(template_type)
        else:
            # Get custom template from database
            try:
                template_id_int = int(template_id)
                custom_template = EmailTemplate.query.filter_by(id=template_id_int, user_id=current_user.id).first()
                
                if custom_template:
                    template_content = custom_template.content
                    # Update required fields based on template
                    if custom_template.required_fields:
                        required_fields = custom_template.required_fields.split(',')
            except ValueError:
                return jsonify({
                    'success': False,
                    'errors': ['Invalid template ID']
                })
        
        if not template_content:
            return jsonify({
                'success': False,
                'errors': ['Template not found']
            })
        
        # Check for required fields in CSV
        missing_fields = [field for field in required_fields if field not in csv_reader.fieldnames]
        if missing_fields:
            return jsonify({
                'success': False,
                'errors': [f'Missing required fields in CSV: {", ".join(missing_fields)}']
            })
        
        # Reset the CSV reader
        csv_io.seek(0)
        next(csv_reader)  # Skip the header row
        
        # Process each row
        result = {
            'success': True,
            'total_recipients': 0,
            'successful_recipients': 0,
            'emails': [],
            'errors': []
        }
        
        for row_num, row in enumerate(csv_reader, start=2):
            # Skip empty rows
            if not any(row.values()):
                continue
            
            # Check for required fields
            if not all(row.get(field, '') for field in required_fields):
                missing = [field for field in required_fields if not row.get(field, '')]
                result['errors'].append(f"Row {row_num}: Missing values for {', '.join(missing)}")
                continue
            
            result['total_recipients'] += 1
            
            try:
                # Generate email
                generated_email = EmailGenerator.generate_email_from_template(row, template_content)
                
                recipient_data = {
                    'name': row.get('name', ''),
                    'email': row.get('email', ''),
                    'company': row.get('company', ''),
                    'role': row.get('role', '')
                }
                
                result['emails'].append({
                    'recipient': recipient_data,
                    'email': generated_email
                })
                result['successful_recipients'] += 1
            except Exception as e:
                result['errors'].append(f"Row {row_num}: Error generating email - {str(e)}")
            
        # Update success flag if we have any emails
        if result['successful_recipients'] == 0 and result['total_recipients'] > 0:
            result['success'] = False
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Error processing bulk emails: {str(e)}")
        return jsonify({
            'success': False,
            'errors': [f'Server error: {str(e)}']
        }), 500

@app.route('/auth/login')
def login_page():
    """Redirect to auth login route"""
    return redirect(url_for('auth.login'))

@app.route('/auth/register')
def register_page():
    """Redirect to auth register route"""
    return redirect(url_for('auth.register'))

@app.route('/api/templates', methods=['GET'])
@login_required
def get_all_templates():
    """API endpoint to get all available email templates (default and custom)"""
    try:
        # Get default templates
        default_templates = [
            {
                'id': 'default_cold_email',
                'name': 'Cold Email',
                'type': 'default',
                'description': 'Default template for cold outreach',
                'content': EmailGenerator.get_default_template('cold_email')
            },
            {
                'id': 'default_follow_up',
                'name': 'Follow Up',
                'type': 'default',
                'description': 'Default template for following up with prospects',
                'content': EmailGenerator.get_default_template('follow_up')
            },
            {
                'id': 'default_meeting_request',
                'name': 'Meeting Request',
                'type': 'default',
                'description': 'Default template for requesting meetings',
                'content': EmailGenerator.get_default_template('meeting_request')
            }
        ]
        
        # Get user's custom templates from database
        custom_templates = EmailTemplate.query.filter_by(user_id=current_user.id).all()
        
        # Convert to list of dictionaries
        custom_templates_list = []
        for template in custom_templates:
            custom_templates_list.append({
                'id': template.id,
                'name': template.name,
                'type': 'custom',
                'description': template.description,
                'content': template.content,
                'required_fields': template.required_fields.split(',')
            })
        
        # Combine all templates
        all_templates = default_templates + custom_templates_list
        
        return jsonify({
            'success': True,
            'templates': all_templates
        })
    
    except Exception as e:
        print(f"Error retrieving templates: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/templates/<template_id>', methods=['GET'])
@login_required
def get_template(template_id):
    """API endpoint to get a specific email template"""
    try:
        if template_id.startswith('default_'):
            # Return a default template
            template_type = template_id.replace('default_', '')
            template_content = EmailGenerator.get_default_template(template_type)
            
            return jsonify({
                'success': True,
                'template': {
                    'id': template_id,
                    'name': template_type.replace('_', ' ').title(),
                    'type': 'default',
                    'content': template_content,
                    'required_fields': ['name', 'company', 'role', 'email']
                }
            })
        else:
            # Fetch custom template from database
            try:
                template_id_int = int(template_id)
                template = EmailTemplate.query.filter_by(id=template_id_int, user_id=current_user.id).first()
                
                if not template:
                    return jsonify({
                        'success': False,
                        'error': 'Template not found'
                    }), 404
                
                return jsonify({
                    'success': True,
                    'template': {
                        'id': template.id,
                        'name': template.name,
                        'type': 'custom',
                        'description': template.description,
                        'content': template.content,
                        'required_fields': template.required_fields.split(',')
                    }
                })
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid template ID'
                }), 400
    
    except Exception as e:
        print(f"Error retrieving template: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/pricing')
def pricing():
    """Render the pricing page - public access"""
    # Show different UI elements based on authentication status
    user_tier = "Free"
    email_usage = 0
    bulk_campaigns = 0
    
    if current_user.is_authenticated:
        # In a real app, get this data from the user's subscription record
        user_tier = getattr(current_user, 'subscription_tier', "Free")
        email_usage = 145  # Example usage data
        bulk_campaigns = 12  # Example usage data
    
    plans = {
        "free": {
            "name": "Free",
            "price_monthly": 0,
            "price_annual": 0,
            "emails_per_month": 1,
            "features": ["Single email personalization", "Basic templates", "Email preview"],
            "unavailable": ["Bulk email generation", "Custom templates", "Advanced analytics"]
        },
        "basic": {
            "name": "Basic",
            "price_monthly": 19,
            "price_annual": 15,
            "emails_per_month": 100,
            "features": ["Single email personalization", "Up to 100 bulk emails/month", 
                        "All templates", "Basic analytics"],
            "unavailable": ["Custom templates", "Priority support"]
        },
        "professional": {
            "name": "Professional",
            "price_monthly": 49,
            "price_annual": 39,
            "emails_per_month": 1000,
            "features": ["Single email personalization", "Up to 1,000 bulk emails/month", 
                        "Advanced templates", "Custom templates", "Advanced analytics", "Email scheduling"],
            "unavailable": []
        },
        "enterprise": {
            "name": "Enterprise",
            "price_monthly": 99,
            "price_annual": 79,
            "emails_per_month": 0,  # Unlimited
            "features": ["Unlimited email personalization", "Unlimited bulk emails", 
                        "All templates + priority access", "Premium analytics", "Advanced customization", 
                        "Priority support 24/7"],
            "unavailable": []
        }
    }
    
    return render_template('pricing.html', user_tier=user_tier, 
                          email_usage=email_usage, bulk_campaigns=bulk_campaigns, 
                          plans=plans)

@app.route('/subscription')
@login_required
def subscription():
    """Render the subscription management page"""
    # In a real app, these would be fetched from the database
    custom_templates_count = 5  # Example count
    
    # Reuse the plans data from the pricing page
    plans = {
        "free": {
            "name": "Free",
            "price_monthly": 0,
            "price_annual": 0,
            "emails_per_month": 1,
            "features": ["Single email personalization", "Basic templates", "Email preview"],
            "unavailable": ["Bulk email generation", "Custom templates", "Advanced analytics"]
        },
        "basic": {
            "name": "Basic",
            "price_monthly": 19,
            "price_annual": 15,
            "emails_per_month": 100,
            "features": ["Single email personalization", "Up to 100 bulk emails/month", 
                        "All templates", "Basic analytics"],
            "unavailable": ["Custom templates", "Priority support"]
        },
        "professional": {
            "name": "Professional",
            "price_monthly": 49,
            "price_annual": 39,
            "emails_per_month": 1000,
            "features": ["Single email personalization", "Up to 1,000 bulk emails/month", 
                        "Advanced templates", "Custom templates", "Advanced analytics", "Email scheduling"],
            "unavailable": []
        },
        "enterprise": {
            "name": "Enterprise",
            "price_monthly": 99,
            "price_annual": 79,
            "emails_per_month": 0,  # Unlimited
            "features": ["Unlimited email personalization", "Unlimited bulk emails", 
                        "All templates + priority access", "Premium analytics", "Advanced customization", 
                        "Priority support 24/7"],
            "unavailable": []
        }
    }
    
    return render_template('subscription.html', user=current_user, 
                           custom_templates_count=custom_templates_count, plans=plans)

@app.route('/upgrade-subscription', methods=['POST'])
@login_required
def upgrade_subscription():
    """Handle subscription upgrades"""
    if request.method == 'POST':
        plan = request.form.get('plan')
        billing_cycle = request.form.get('billing_cycle', 'monthly')
        
        # In a real app, you would:
        # 1. Verify payment information
        # 2. Process the payment
        # 3. Update the subscription in the database
        
        # Maps plan keys to subscription tier names
        plan_tiers = {
            'free': 'Free',
            'basic': 'Basic',
            'professional': 'Professional',
            'enterprise': 'Enterprise'
        }
        
        if plan in plan_tiers:
            # Update user's subscription information
            current_user.subscription_tier = plan_tiers[plan]
            current_user.is_annual_billing = (billing_cycle == 'annual')
            
            # Set subscription dates
            now = datetime.now()
            current_user.subscription_start_date = now
            
            # Set end date based on billing cycle
            if billing_cycle == 'annual':
                current_user.subscription_end_date = now + dt.timedelta(days=365)
            else:
                current_user.subscription_end_date = now + dt.timedelta(days=30)
            
            # Save changes to the database
            db.session.commit()
            flash(f'Successfully upgraded to {plan_tiers[plan]} plan!', 'success')
        else:
            flash('Invalid plan selected', 'danger')
            
    return redirect(url_for('subscription'))

@app.route('/update-billing-cycle', methods=['POST'])
@login_required
def update_billing_cycle():
    """Update the billing cycle (monthly/annual)"""
    if request.method == 'POST':
        billing_cycle = request.form.get('billing_cycle', 'monthly')
        
        # Update the billing cycle
        is_annual = (billing_cycle == 'annual')
        current_user.is_annual_billing = is_annual
        
        # Update subscription end date based on new billing cycle
        now = datetime.now()
        if is_annual:
            current_user.subscription_end_date = now + dt.timedelta(days=365)
            savings = "20%"
        else:
            current_user.subscription_end_date = now + dt.timedelta(days=30)
            savings = "0%"
        
        # Save changes to the database
        db.session.commit()
        
        # Notify the user
        flash(f'Successfully updated to {billing_cycle} billing (saving {savings})', 'success')
        
    return redirect(url_for('subscription'))

@app.route('/downgrade-to-free', methods=['POST'])
@login_required
def downgrade_to_free():
    """Downgrade subscription to the free tier"""
    if request.method == 'POST':
        # In a real app, you would handle cancellation logic, pro-rating, etc.
        
        # Set the user's subscription to Free
        current_user.subscription_tier = 'Free'
        current_user.subscription_end_date = None
        
        # Save changes to the database
        db.session.commit()
        
        # Notify the user
        flash('Successfully downgraded to Free plan', 'success')
        
    return redirect(url_for('subscription'))

@app.route('/email-settings')
@login_required
def email_settings():
    """Render the email settings page"""
    # Get user's SMTP configurations
    smtp_configs = SMTPConfig.query.filter_by(user_id=current_user.id).all()
    
    # Get user's email history
    email_history = EmailHistory.query.filter_by(user_id=current_user.id).order_by(EmailHistory.sent_at.desc()).limit(10).all()
    
    return render_template('email_settings.html', 
                          smtp_configs=smtp_configs,
                          email_history=email_history)

@app.route('/add-smtp-config', methods=['POST'])
@login_required
def add_smtp_config():
    """Add a new SMTP server configuration"""
    try:
        # If this is marked as default, unset other configs as default
        if request.form.get('is_default'):
            SMTPConfig.query.filter_by(user_id=current_user.id, is_default=True).update({'is_default': False})
            db.session.commit()
        
        # Create new SMTP config
        smtp_config = SMTPConfig(
            user_id=current_user.id,
            name=request.form.get('name'),
            server=request.form.get('server'),
            port=int(request.form.get('port')),
            use_tls=bool(request.form.get('use_tls')),
            username=request.form.get('username'),
            password=request.form.get('password'),
            email=request.form.get('email'),
            display_name=request.form.get('display_name'),
            reply_to=request.form.get('reply_to'),
            is_default=bool(request.form.get('is_default'))
        )
        
        db.session.add(smtp_config)
        db.session.commit()
        
        flash('SMTP configuration added successfully', 'success')
    except Exception as e:
        flash(f'Error adding SMTP configuration: {str(e)}', 'danger')
    
    return redirect(url_for('email_settings'))

@app.route('/update-smtp-config', methods=['POST'])
@login_required
def update_smtp_config():
    """Update an existing SMTP server configuration"""
    try:
        config_id = request.form.get('config_id')
        smtp_config = SMTPConfig.query.filter_by(id=config_id, user_id=current_user.id).first()
        
        if not smtp_config:
            flash('SMTP configuration not found', 'danger')
            return redirect(url_for('email_settings'))
        
        # Update config details
        smtp_config.name = request.form.get('name')
        smtp_config.server = request.form.get('server')
        smtp_config.port = int(request.form.get('port'))
        smtp_config.use_tls = bool(request.form.get('use_tls'))
        smtp_config.username = request.form.get('username')
        
        # Only update password if provided
        if request.form.get('password').strip():
            smtp_config.password = request.form.get('password')
            
        smtp_config.email = request.form.get('email')
        smtp_config.display_name = request.form.get('display_name')
        smtp_config.reply_to = request.form.get('reply_to')
        
        db.session.commit()
        flash('SMTP configuration updated successfully', 'success')
    except Exception as e:
        flash(f'Error updating SMTP configuration: {str(e)}', 'danger')
    
    return redirect(url_for('email_settings'))

@app.route('/delete-smtp-config', methods=['POST'])
@login_required
def delete_smtp_config():
    """Delete an SMTP server configuration"""
    try:
        config_id = request.form.get('config_id')
        smtp_config = SMTPConfig.query.filter_by(id=config_id, user_id=current_user.id).first()
        
        if not smtp_config:
            flash('SMTP configuration not found', 'danger')
            return redirect(url_for('email_settings'))
        
        # If deleting default config, set another one as default if available
        if smtp_config.is_default:
            other_config = SMTPConfig.query.filter(
                SMTPConfig.user_id == current_user.id,
                SMTPConfig.id != smtp_config.id
            ).first()
            
            if other_config:
                other_config.is_default = True
                
        db.session.delete(smtp_config)
        db.session.commit()
        flash('SMTP configuration deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting SMTP configuration: {str(e)}', 'danger')
    
    return redirect(url_for('email_settings'))

@app.route('/set-default-smtp', methods=['POST'])
@login_required
def set_default_smtp():
    """Set an SMTP configuration as default"""
    try:
        config_id = request.form.get('config_id')
        
        # Unset all configs as default
        SMTPConfig.query.filter_by(user_id=current_user.id).update({'is_default': False})
        
        # Set the selected config as default
        smtp_config = SMTPConfig.query.filter_by(id=config_id, user_id=current_user.id).first()
        if smtp_config:
            smtp_config.is_default = True
            db.session.commit()
            flash('Default SMTP server updated successfully', 'success')
        else:
            flash('SMTP configuration not found', 'danger')
    except Exception as e:
        flash(f'Error updating default SMTP server: {str(e)}', 'danger')
    
    return redirect(url_for('email_settings'))

@app.route('/get-smtp-config/<int:config_id>')
@login_required
def get_smtp_config(config_id):
    """Get SMTP configuration details for editing"""
    smtp_config = SMTPConfig.query.filter_by(id=config_id, user_id=current_user.id).first()
    
    if smtp_config:
        return jsonify({
            'success': True,
            'config': smtp_config.to_dict()
        })
    else:
        return jsonify({
            'success': False,
            'message': 'SMTP configuration not found'
        })

@app.route('/test-smtp-connection/<int:config_id>', methods=['POST'])
@login_required
def test_smtp_connection(config_id):
    """Test an SMTP server connection"""
    try:
        smtp_config = SMTPConfig.query.filter_by(id=config_id, user_id=current_user.id).first()
        
        if not smtp_config:
            return jsonify({
                'success': False,
                'message': 'SMTP configuration not found'
            })
        
        # Test connection with EmailService
        success, message = EmailService.test_smtp_connection(smtp_config.to_smtp_config())
        
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error testing connection: {str(e)}'
        })

@app.route('/send-email', methods=['POST'])
@login_required
def send_email():
    """Send a single email using configured SMTP server"""
    try:
        # Get form data
        recipient = request.json.get('recipient')
        subject = request.json.get('subject')
        content = request.json.get('content')
        config_id = request.json.get('smtp_config_id')
        
        # Validate input
        if not all([recipient, subject, content]):
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            })
        
        # Get SMTP config (use default if not specified)
        if config_id:
            smtp_config = SMTPConfig.query.filter_by(id=config_id, user_id=current_user.id).first()
        else:
            smtp_config = SMTPConfig.query.filter_by(user_id=current_user.id, is_default=True).first()
        
        if not smtp_config:
            return jsonify({
                'success': False,
                'message': 'No SMTP configuration available'
            })
        
        # Send email
        success, message = EmailService.send_email(
            recipient_email=recipient,
            subject=subject,
            html_content=content,
            smtp_config=smtp_config.to_smtp_config()
        )
        
        # Record in email history
        email_history = EmailHistory(
            user_id=current_user.id,
            recipient=recipient,
            subject=subject,
            status='sent' if success else 'failed',
            error_message=None if success else message
        )
        
        db.session.add(email_history)
        db.session.commit()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Email sent successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Failed to send email: {message}'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error sending email: {str(e)}'
        })

@app.route('/delete-template/<int:template_id>', methods=['POST'])
@login_required
def delete_template(template_id):
    """Delete a custom email template"""
    try:
        # Find the template in the database
        template = EmailTemplate.query.filter_by(id=template_id, user_id=current_user.id).first()
        
        if not template:
            return jsonify({
                'success': False,
                'message': 'Template not found or you do not have permission to delete it'
            }), 404
        
        # Get template name for the success message
        template_name = template.name
        
        # Delete the template
        db.session.delete(template)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Template "{template_name}" deleted successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting template: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error deleting template: {str(e)}'
        }), 500

# Create error templates directory if it doesn't exist
# @app.before_first_request  # This decorator was removed in Flask 2.3+
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
    # Call function to create error templates directory during startup
    # This replaces the removed @app.before_first_request decorator
    create_error_templates()
    app.run(debug=True)
