from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import os

# Initialize SQLAlchemy
db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password = db.Column(db.String(200), nullable=False)
    
    # User profile info
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Fields for email verification
    email_confirmed = db.Column(db.Boolean, default=False)
    email_confirm_token = db.Column(db.String(128))
    
    # Fields for password reset
    reset_token = db.Column(db.String(128))
    reset_token_expiration = db.Column(db.DateTime)
    
    # Fields for OAuth login
    oauth_provider = db.Column(db.String(20))
    oauth_id = db.Column(db.String(80))
    
    # Fields for 2FA
    mfa_enabled = db.Column(db.Boolean, default=False)
    mfa_secret = db.Column(db.String(32))
    
    # Security fields
    login_attempts = db.Column(db.Integer, default=0)
    account_locked = db.Column(db.Boolean, default=False)
    account_locked_until = db.Column(db.DateTime, nullable=True)
    
    def get_id(self):
        """Required by Flask-Login"""
        return str(self.id)
    
    # Database fields for subscription data
    subscription_tier = db.Column(db.String(20), default='Basic')
    subscription_start_date = db.Column(db.DateTime, nullable=True)
    subscription_end_date = db.Column(db.DateTime, nullable=True)
    is_annual_billing = db.Column(db.Boolean, default=False)
    emails_generated = db.Column(db.Integer, default=0)
    emails_sent = db.Column(db.Integer, default=0)
    bulk_campaigns = db.Column(db.Integer, default=0)
    current_month_usage = db.Column(db.Integer, default=0)

    def get_monthly_email_limit(self):
        """Get the monthly email limit based on subscription tier"""
        limits = {
            'Basic': 100,
            'Professional': 1000,
            'Enterprise': float('inf')  # Unlimited
        }
        return limits.get(self.subscription_tier, 100)
    
    def can_send_bulk_emails(self):
        """Check if user can send bulk emails (all tiers)"""
        return True
    
    def can_create_custom_templates(self):
        """Check if user can create custom templates (Professional and Enterprise tiers)"""
        return self.subscription_tier in ['Professional', 'Enterprise']
    
    def get_remaining_emails(self):
        """Get the number of emails remaining in the current month"""
        limit = self.get_monthly_email_limit()
        if limit == float('inf'):
            return float('inf')
        return max(0, limit - self.current_month_usage)
    
    def has_unlimited_emails(self):
        """Check if the user has unlimited email sending (Enterprise plan)"""
        return self.subscription_tier == 'Enterprise'
    
    def reset_monthly_usage(self):
        """Reset the monthly usage counter"""
        self.current_month_usage = 0
        db.session.commit()
    
    def increment_usage(self, count=1):
        """Increment the usage counters"""
        self.emails_generated += count
        self.current_month_usage += count
        db.session.commit()
    
    def record_bulk_campaign(self, email_count):
        """Record a bulk campaign and its usage"""
        self.bulk_campaigns += 1
        self.emails_sent += email_count
        self.increment_usage(email_count)
    
    def __repr__(self):
        return f'<User {self.username}>'


class SMTPConfig(db.Model):
    """Model for storing SMTP server configurations"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('smtp_configs', lazy=True))
    
    # Configuration name for users with multiple SMTP configs
    name = db.Column(db.String(100), nullable=False, default="Default")
    
    # SMTP server details
    server = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, nullable=False, default=587)
    use_tls = db.Column(db.Boolean, default=True)
    
    # Authentication details
    username = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    
    # Sender information
    email = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(255))
    
    # Default reply-to address
    reply_to = db.Column(db.String(255))
    
    # Tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Is this the user's default SMTP configuration?
    is_default = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        """Convert SMTP config to dictionary (without password)"""
        return {
            'id': self.id,
            'name': self.name,
            'server': self.server,
            'port': self.port,
            'use_tls': self.use_tls,
            'username': self.username,
            'email': self.email,
            'display_name': self.display_name,
            'reply_to': self.reply_to,
            'is_default': self.is_default,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_smtp_config(self):
        """Convert to format needed by EmailService"""
        return {
            'server': self.server,
            'port': self.port,
            'use_tls': self.use_tls,
            'username': self.username,
            'password': self.password,
            'email': self.email,
            'name': self.display_name
        }
    
    def __repr__(self):
        return f'<SMTPConfig {self.name} ({self.server})>'


class EmailHistory(db.Model):
    """Model for tracking sent emails"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('email_history', lazy=True))
    
    # Email details
    recipient = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    campaign_name = db.Column(db.String(255))  # For bulk emails
    
    # Tracking
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="sent")  # sent, failed, etc.
    error_message = db.Column(db.Text)
    
    # Analytics
    opened = db.Column(db.Boolean, default=False)
    opened_at = db.Column(db.DateTime)
    clicked = db.Column(db.Boolean, default=False)
    clicked_at = db.Column(db.DateTime)
    
    # Store email content for reference
    content = db.Column(db.Text)
    
    # Reference to the SMTP configuration used
    smtp_config_id = db.Column(db.Integer, db.ForeignKey('smtp_config.id'), nullable=True)
    smtp_config = db.relationship('SMTPConfig', backref=db.backref('emails_sent', lazy=True))
    
    def __repr__(self):
        return f'<EmailHistory {self.recipient} ({self.sent_at})>'


class EmailTemplate(db.Model):
    """Model for custom email templates"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('email_templates', lazy=True))
    
    # Template details
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    content = db.Column(db.Text, nullable=False)
    
    # Template type (cold_email, follow_up, meeting_request, custom)
    template_type = db.Column(db.String(50), default="custom")
    
    # Required fields (stored as comma-separated list)
    required_fields = db.Column(db.String(255), default="name,company,role")
    
    # Tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Is this a public template?
    is_public = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        """Convert template to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'content': self.content,
            'template_type': self.template_type,
            'required_fields': self.required_fields.split(',') if self.required_fields else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_public': self.is_public
        }
    
    def __repr__(self):
        return f'<EmailTemplate {self.name}>'


class LoginAttempt(db.Model):
    """Model to track login attempts for security monitoring"""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    success = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<LoginAttempt {self.email} {self.timestamp}>'


class UserSession(db.Model):
    """Model to track active user sessions"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_id = db.Column(db.String(128), unique=True, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('sessions', lazy=True))
    
    def __repr__(self):
        return f'<UserSession {self.user_id} {self.session_id[:10]}>'
