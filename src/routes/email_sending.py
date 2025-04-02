from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime
import time
from ..models import EmailHistory, EmailTemplate, SMTPConfig, db
from ..utils.email_generator import EmailGenerator
from ..email_service import EmailService

email_bp = Blueprint('email', __name__, url_prefix='/email')

@email_bp.route('/bulk')
@login_required
def bulk():
    """Render the bulk email generation page"""
    # Get user's custom templates from database
    custom_templates = EmailTemplate.query.filter_by(user_id=current_user.id).all()
    
    # Get the user's smtp configs
    smtp_configs = SMTPConfig.query.filter_by(user_id=current_user.id).all()
    
    return render_template('bulk.html', custom_templates=custom_templates, smtp_configs=smtp_configs)

@email_bp.route('/bulk-emails-alias')
@login_required
def bulk_emails_alias():
    """Alias for bulk_emails to maintain backward compatibility"""
    return redirect(url_for('email.bulk'))

@email_bp.route('/send-bulk-emails', methods=['POST'])
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

@email_bp.route('/generate-email', methods=['POST'])
@login_required
def email_generator():
    """API endpoint to generate a personalized email"""
    data = request.json
    
    # Check if a specific template was requested
    template_type = data.get('template', 'cold_email')
    
    # Generate the email using the selected template
    email_content = EmailGenerator.generate_email(recipient_data=data, template_type=template_type)
    
    return jsonify({'email': email_content})

@email_bp.route('/send', methods=['POST'])
@login_required
def send_email():
    """Send a single email using configured SMTP server"""
    try:
        # Get form data
        smtp_config_id = request.form.get('smtp_config_id')
        recipient = request.form.get('recipient')
        subject = request.form.get('subject')
        html_content = request.form.get('content')
        
        # Validate required fields
        if not all([smtp_config_id, recipient, subject, html_content]):
            flash('Please fill all required fields', 'danger')
            return redirect(url_for('email.bulk'))
        
        # Get SMTP config
        smtp_config = SMTPConfig.query.get(smtp_config_id)
        if not smtp_config or smtp_config.user_id != current_user.id:
            flash('Invalid SMTP configuration', 'danger')
            return redirect(url_for('email.bulk'))
        
        # Create email history record
        email_history = EmailHistory(
            user_id=current_user.id,
            recipient=recipient,
            subject=subject,
            content=html_content,
            smtp_config_id=smtp_config.id
        )
        db.session.add(email_history)
        db.session.commit()
        
        # Add tracking to the email content
        base_url = request.host_url.rstrip('/')
        html_content = EmailService.add_tracking_pixel(html_content, email_history.id, base_url)
        html_content = EmailService.add_click_tracking(html_content, email_history.id, base_url)
        
        # Send the email
        smtp_config_dict = smtp_config.to_smtp_config()
        success, message = EmailService.send_email(
            recipient_email=recipient,
            subject=subject,
            html_content=html_content,
            smtp_config=smtp_config_dict
        )
        
        # Update email history with status
        email_history.status = 'sent' if success else 'failed'
        if not success:
            email_history.error_message = message
        db.session.commit()
        
        # Increment usage counter
        current_user.increment_usage()
        
        # Flash message
        if success:
            flash('Email sent successfully', 'success')
        else:
            flash(f'Failed to send email: {message}', 'danger')
            
        return redirect(url_for('email.bulk'))
        
    except Exception as e:
        flash(f'Error sending email: {str(e)}', 'danger')
        return redirect(url_for('email.bulk'))

@email_bp.route('/process-bulk-emails', methods=['POST'])
@login_required
def process_bulk_emails():
    """API endpoint to process bulk emails"""
    if not current_user.is_authenticated:
        return jsonify({
            'success': False,
            'message': 'Authentication required'
        })
    
    try:
        # Get JSON data
        data = request.json
        
        # Validate input
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            })
        
        # Extract data
        smtp_config_id = data.get('smtp_config_id')
        emails = data.get('emails', [])
        campaign_name = data.get('campaign_name')
        delay = int(data.get('delay', 2))
        
        # Validate required fields
        if not all([smtp_config_id, emails, campaign_name]):
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            })
        
        # Get SMTP config
        smtp_config = SMTPConfig.query.get(smtp_config_id)
        if not smtp_config or smtp_config.user_id != current_user.id:
            return jsonify({
                'success': False,
                'message': 'Invalid SMTP configuration'
            })
        
        # Get base URL for tracking
        base_url = request.host_url.rstrip('/')
        
        # Configure SMTP settings
        smtp_config_dict = smtp_config.to_smtp_config()
        
        # Validate recipients and email content
        if not emails or not isinstance(emails, list):
            return jsonify({
                'success': False,
                'message': 'Invalid email data'
            })
        
        results = {
            'success': True,
            'total': len(emails),
            'sent': 0,
            'failed': 0,
            'errors': []
        }
        
        # Create email history records first to get IDs for tracking
        email_records = []
        for email_data in emails:
            # Extract recipient and content
            recipient = email_data.get('recipient')
            subject = email_data.get('subject')
            content = email_data.get('content')
            
            # Create email history record
            email_history = EmailHistory(
                user_id=current_user.id,
                recipient=recipient,
                subject=subject,
                content=content,
                campaign_name=campaign_name,
                smtp_config_id=smtp_config.id
            )
            db.session.add(email_history)
            
            # Store for later processing
            email_records.append({
                'record': email_history,
                'recipient': recipient,
                'subject': subject,
                'content': content
            })
        
        # Commit to get IDs assigned
        db.session.commit()
        
        # Process each email with tracking
        for email_data in email_records:
            record = email_data['record']
            recipient = email_data['recipient']
            subject = email_data['subject']
            content = email_data['content']
            
            try:
                # Add tracking to the email content
                tracked_content = EmailService.add_tracking_pixel(content, record.id, base_url)
                tracked_content = EmailService.add_click_tracking(tracked_content, record.id, base_url)
                
                # Send the email
                success, message = EmailService.send_email(
                    recipient_email=recipient,
                    subject=subject,
                    html_content=tracked_content,
                    smtp_config=smtp_config_dict
                )
                
                # Update record with status
                record.status = 'sent' if success else 'failed'
                if not success:
                    record.error_message = message
                    results['failed'] += 1
                    results['errors'].append(f"Failed to send to {recipient}: {message}")
                else:
                    results['sent'] += 1
                
                # Add delay between emails if specified
                if delay > 0:
                    time.sleep(delay)
                    
            except Exception as e:
                # Update record with error
                record.status = 'failed'
                record.error_message = str(e)
                results['failed'] += 1
                results['errors'].append(f"Error sending to {recipient}: {str(e)}")
        
        # Commit all updates
        db.session.commit()
        
        # Update user stats
        current_user.record_bulk_campaign(len(emails))
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error processing bulk emails: {str(e)}'
        })
