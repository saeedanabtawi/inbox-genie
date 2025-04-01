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
    email_confirm_token = db.Column(db.String(32))
    
    # Fields for password reset
    reset_token = db.Column(db.String(32))
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
    
    # In-memory subscription data (not stored in database)
    # This is a temporary development solution
    _subscription_data = {}
    
    def _get_subscription_data(self, key, default):
        """Get subscription data from in-memory storage"""
        user_data = self._subscription_data.get(self.id, {})
        return user_data.get(key, default)
    
    def _set_subscription_data(self, key, value):
        """Set subscription data in in-memory storage"""
        if self.id not in self._subscription_data:
            self._subscription_data[self.id] = {}
        self._subscription_data[self.id][key] = value
    
    # Subscription tier property
    @property
    def subscription_tier(self):
        """Get user's subscription tier"""
        return self._get_subscription_data('tier', 'Free')
    
    @subscription_tier.setter
    def subscription_tier(self, value):
        """Set user's subscription tier"""
        self._set_subscription_data('tier', value)
    
    # Subscription dates
    @property
    def subscription_start_date(self):
        """Get subscription start date"""
        return self._get_subscription_data('start_date', None)
    
    @subscription_start_date.setter
    def subscription_start_date(self, value):
        """Set subscription start date"""
        self._set_subscription_data('start_date', value)
    
    @property
    def subscription_end_date(self):
        """Get subscription end date"""
        return self._get_subscription_data('end_date', None)
    
    @subscription_end_date.setter
    def subscription_end_date(self, value):
        """Set subscription end date"""
        self._set_subscription_data('end_date', value)
    
    # Billing cycle
    @property
    def is_annual_billing(self):
        """Get annual billing status"""
        return self._get_subscription_data('annual_billing', False)
    
    @is_annual_billing.setter
    def is_annual_billing(self, value):
        """Set annual billing status"""
        self._set_subscription_data('annual_billing', value)
    
    # Usage metrics
    @property
    def emails_generated(self):
        """Get emails generated count"""
        return self._get_subscription_data('emails_generated', 0)
    
    @emails_generated.setter
    def emails_generated(self, value):
        """Set emails generated count"""
        self._set_subscription_data('emails_generated', value)
    
    @property
    def emails_sent(self):
        """Get emails sent count"""
        return self._get_subscription_data('emails_sent', 0)
    
    @emails_sent.setter
    def emails_sent(self, value):
        """Set emails sent count"""
        self._set_subscription_data('emails_sent', value)
    
    @property
    def bulk_campaigns(self):
        """Get bulk campaigns count"""
        return self._get_subscription_data('bulk_campaigns', 0)
    
    @bulk_campaigns.setter
    def bulk_campaigns(self, value):
        """Set bulk campaigns count"""
        self._set_subscription_data('bulk_campaigns', value)
    
    @property
    def current_month_usage(self):
        """Get current month usage"""
        return self._get_subscription_data('current_month_usage', 0)
    
    @current_month_usage.setter
    def current_month_usage(self, value):
        """Set current month usage"""
        self._set_subscription_data('current_month_usage', value)
    
    def get_monthly_email_limit(self):
        """Get the monthly email limit based on subscription tier"""
        limits = {
            'Free': 1,
            'Basic': 100,
            'Professional': 1000,
            'Enterprise': float('inf')  # Unlimited
        }
        return limits.get(self.subscription_tier, 1)
    
    def can_send_bulk_emails(self):
        """Check if user can send bulk emails (any paid tier)"""
        return self.subscription_tier != 'Free'
    
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
    
    def increment_usage(self, count=1):
        """Increment the usage counters"""
        self.emails_generated = self.emails_generated + count
        self.current_month_usage = self.current_month_usage + count
    
    def record_bulk_campaign(self, email_count):
        """Record a bulk campaign and its usage"""
        self.bulk_campaigns = self.bulk_campaigns + 1
        self.emails_sent = self.emails_sent + email_count
        self.increment_usage(email_count)
    
    def __repr__(self):
        return f'<User {self.username}>'

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
