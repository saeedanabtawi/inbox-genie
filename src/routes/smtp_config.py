from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from ..models import SMTPConfig, EmailHistory, db
from ..email_service import EmailService

smtp_bp = Blueprint('smtp', __name__, url_prefix='/smtp')

@smtp_bp.route('/settings')
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

@smtp_bp.route('/add', methods=['POST'])
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
    
    return redirect(url_for('smtp.email_settings'))

@smtp_bp.route('/update', methods=['POST'])
@login_required
def update_smtp_config():
    """Update an existing SMTP server configuration"""
    try:
        config_id = request.form.get('config_id')
        smtp_config = SMTPConfig.query.filter_by(id=config_id, user_id=current_user.id).first()
        
        if not smtp_config:
            flash('SMTP configuration not found', 'danger')
            return redirect(url_for('smtp.email_settings'))
        
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
    
    return redirect(url_for('smtp.email_settings'))

@smtp_bp.route('/delete', methods=['POST'])
@login_required
def delete_smtp_config():
    """Delete an SMTP server configuration"""
    try:
        config_id = request.form.get('config_id')
        smtp_config = SMTPConfig.query.filter_by(id=config_id, user_id=current_user.id).first()
        
        if not smtp_config:
            flash('SMTP configuration not found', 'danger')
            return redirect(url_for('smtp.email_settings'))
        
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
    
    return redirect(url_for('smtp.email_settings'))

@smtp_bp.route('/set-default', methods=['POST'])
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
    
    return redirect(url_for('smtp.email_settings'))

@smtp_bp.route('/get/<int:config_id>')
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

@smtp_bp.route('/test-connection/<int:config_id>', methods=['POST'])
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
