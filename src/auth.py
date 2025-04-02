import os
import functools
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import re
import secrets

# Import database models
from .models import db, User, LoginAttempt, UserSession

# Create blueprint for auth routes
auth_bp = Blueprint('auth', __name__)

# Initialize login manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Serializer for generating secure tokens
def get_serializer(secret_key=None):
    if secret_key is None:
        secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
    return URLSafeTimedSerializer(secret_key)

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return User.query.get(int(user_id))

# Forms for authentication
class LoginForm(FlaskForm):
    """Form for user login"""
    identifier = StringField('Email or Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    """Form for user registration"""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Sign Up')
    
    def validate_username(self, username):
        """Check if username is already taken"""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is already taken. Please choose another one.')
            
    def validate_email(self, email):
        """Check if email is already registered"""
        user = User.query.filter_by(email=email.data.lower()).first()
        if user:
            raise ValidationError('That email is already registered. Please use a different one.')
            
    def validate_password(self, password):
        """Validate password strength"""
        password_str = password.data
        
        # Check for minimum requirements
        if len(password_str) < 8:
            raise ValidationError('Password must be at least 8 characters long.')
            
        # Check for at least one number
        if not re.search(r'\d', password_str):
            raise ValidationError('Password must contain at least one number.')
            
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', password_str):
            raise ValidationError('Password must contain at least one uppercase letter.')
            
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password_str):
            raise ValidationError('Password must contain at least one special character.')

class ResetPasswordRequestForm(FlaskForm):
    """Form for requesting password reset"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

class ResetPasswordForm(FlaskForm):
    """Form for resetting password"""
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Reset Password')
    
    def validate_password(self, password):
        """Validate password strength"""
        password_str = password.data
        
        # Check for minimum requirements
        if len(password_str) < 8:
            raise ValidationError('Password must be at least 8 characters long.')
            
        # Check for at least one number
        if not re.search(r'\d', password_str):
            raise ValidationError('Password must contain at least one number.')
            
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', password_str):
            raise ValidationError('Password must contain at least one uppercase letter.')
            
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password_str):
            raise ValidationError('Password must contain at least one special character.')

# Authentication routes
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
        
    form = LoginForm()
    
    if form.validate_on_submit():
        identifier = form.identifier.data.lower()
        password = form.password.data
        remember = form.remember.data
        
        # Try to find user by email first, then by username
        user = User.query.filter_by(email=identifier).first()
        identifier_type = 'email' if user else 'username'
        
        if not user:
            user = User.query.filter_by(username=identifier).first()
        
        # Create login attempt record with enhanced schema
        login_attempt = LoginAttempt(
            identifier=identifier,
            identifier_type=identifier_type,
            email=identifier if identifier_type == 'email' else None,
            username=identifier if identifier_type == 'username' else None,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string,
            success=False
        )
        
        # Check if user exists and password is correct
        if user and check_password_hash(user.password, password):
            # Check if account is locked
            if user.account_locked and user.account_locked_until > datetime.utcnow():
                flash('This account is temporarily locked. Please try again later or reset your password.', 'danger')
                db.session.add(login_attempt)
                db.session.commit()
                return render_template('auth/login.html', form=form)
                
            # Reset login attempts on successful login
            user.login_attempts = 0
            user.account_locked = False
            user.last_login = datetime.utcnow()
            
            # Update login attempt record
            login_attempt.success = True
            db.session.add(login_attempt)
            
            # Create user session record
            session_id = secrets.token_hex(64)
            expires_at = datetime.utcnow() + timedelta(days=30 if remember else 1)
            user_session = UserSession(
                user_id=user.id,
                session_id=session_id,
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string,
                expires_at=expires_at
            )
            db.session.add(user_session)
            
            # Log in user
            login_user(user, remember=remember)
            db.session.commit()
            
            # Store session ID in Flask session
            session['session_id'] = session_id
            
            # Redirect to requested page or home
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.home'))
        else:
            # Handle failed login attempts
            if user:
                user.login_attempts += 1
                
                # Lock account after 5 failed attempts
                if user.login_attempts >= 5:
                    user.account_locked = True
                    user.account_locked_until = datetime.utcnow() + timedelta(minutes=30)
                    flash('Too many failed login attempts. Your account has been locked for 30 minutes.', 'danger')
                else:
                    flash('Invalid credentials. Please try again.', 'danger')
            else:
                flash('Invalid credentials. Please try again.', 'danger')
                
            db.session.add(login_attempt)
            db.session.commit()
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration"""
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
        
    form = RegistrationForm()
    
    if form.validate_on_submit():
        # Create new user
        hashed_password = generate_password_hash(form.password.data)
        email_confirm_token = secrets.token_hex(32)
        
        user = User(
            username=form.username.data,
            email=form.email.data.lower(),
            password=hashed_password,
            email_confirm_token=email_confirm_token,
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Generate confirmation token
        serializer = get_serializer()
        token = serializer.dumps(user.email, salt='email-confirm')
        
        # Send confirmation email (implement email sending function)
        # send_confirmation_email(user, token)
        
        flash('Your account has been created! Please check your email to verify your account.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    # Invalidate current session
    if 'session_id' in session:
        user_session = UserSession.query.filter_by(
            user_id=current_user.id,
            session_id=session['session_id']
        ).first()
        
        if user_session:
            user_session.is_active = False
            db.session.commit()
            
    # Clear Flask session
    session.clear()
    
    # Logout user
    logout_user()
    flash('You have been logged out successfully!', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/confirm-email/<token>')
def confirm_email(token):
    """Handle email confirmation"""
    try:
        serializer = get_serializer()
        email = serializer.loads(token, salt='email-confirm', max_age=86400)  # 24 hours expiry
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            if user.email_confirmed:
                flash('Your email has already been confirmed!', 'info')
            else:
                user.email_confirmed = True
                user.email_confirm_token = None
                db.session.commit()
                flash('Your email has been confirmed! You can now log in.', 'success')
                
            return redirect(url_for('auth.login'))
        else:
            flash('The confirmation link is invalid or has expired.', 'danger')
            return redirect(url_for('auth.login'))
            
    except SignatureExpired:
        flash('The confirmation link has expired. Please register again.', 'danger')
        return redirect(url_for('auth.register'))
    except Exception:
        flash('The confirmation link is invalid.', 'danger')
        return redirect(url_for('auth.login'))

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password_request():
    """Handle password reset request"""
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
        
    form = ResetPasswordRequestForm()
    
    if form.validate_on_submit():
        email = form.email.data.lower()
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate reset token
            reset_token = secrets.token_hex(32)
            user.reset_token = reset_token
            user.reset_token_expiration = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            
            # Generate password reset link
            serializer = get_serializer()
            token = serializer.dumps(email, salt='password-reset')
            
            # Send password reset email (implement email sending function)
            # send_password_reset_email(user, token)
            
        # Always show this message even if email not found (security best practice)
        flash('If your email address exists in our database, you will receive a password reset link shortly.', 'info')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/reset_password_request.html', form=form)

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset"""
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
        
    try:
        serializer = get_serializer()
        email = serializer.loads(token, salt='password-reset', max_age=3600)  # 1 hour expiry
        user = User.query.filter_by(email=email).first()
        
        if user is None or not user.reset_token or user.reset_token_expiration < datetime.utcnow():
            flash('The password reset link is invalid or has expired.', 'danger')
            return redirect(url_for('auth.login'))
            
        form = ResetPasswordForm()
        
        if form.validate_on_submit():
            # Update password
            hashed_password = generate_password_hash(form.password.data)
            user.password = hashed_password
            user.reset_token = None
            user.reset_token_expiration = None
            
            # Clear login attempts and unlock account
            user.login_attempts = 0
            user.account_locked = False
            
            db.session.commit()
            
            flash('Your password has been reset! You can now log in with your new password.', 'success')
            return redirect(url_for('auth.login'))
            
        return render_template('auth/reset_password.html', form=form)
        
    except SignatureExpired:
        flash('The password reset link has expired.', 'danger')
        return redirect(url_for('auth.reset_password_request'))
    except Exception:
        flash('The password reset link is invalid.', 'danger')
        return redirect(url_for('auth.login'))

# Session protection middleware
@auth_bp.before_app_request
def check_session_validity():
    """Check if the current session is valid before processing each request"""
    if current_user.is_authenticated and 'session_id' in session:
        # Find the session in the database
        user_session = UserSession.query.filter_by(
            user_id=current_user.id,
            session_id=session['session_id'],
            is_active=True
        ).first()
        
        # If session not found or expired, force logout
        if not user_session or user_session.expires_at < datetime.utcnow():
            logout_user()
            session.clear()
            flash('Your session has expired. Please log in again.', 'info')
            return redirect(url_for('auth.login'))
            
        # Update session expiry if more than halfway through its lifetime
        current_time = datetime.utcnow()
        session_lifetime = (user_session.expires_at - user_session.created_at).total_seconds()
        time_elapsed = (current_time - user_session.created_at).total_seconds()
        
        if time_elapsed > session_lifetime / 2:
            # Extend session
            days = 30 if 'remember' in session else 1
            user_session.expires_at = current_time + timedelta(days=days)
            db.session.commit()

# Initialize the authentication system
def init_auth(app):
    """Initialize authentication components with the Flask app"""
    db.init_app(app)
    login_manager.init_app(app)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    with app.app_context():
        db.create_all()
    
    return app
