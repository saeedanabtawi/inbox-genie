import os
import secrets
from flask import Flask, render_template
from flask_login import LoginManager

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not found, using default environment variables")

# Import models and authentication utilities
from .models import db, User
from .auth import init_auth, login_manager

# Import route blueprints
from .routes.main import main_bp
from .routes.email_tracking import tracking_bp
from .routes.email_templates import templates_bp
from .routes.user_profile import profile_bp
from .routes.email_sending import email_bp
from .routes.smtp_config import smtp_bp

def create_app():
    """Create and configure the Flask application"""
    # Initialize Flask app
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
    
    # Configure SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///inbox_genie.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize authentication (this will also initialize db and login_manager)
    app = init_auth(app)
    
    # The login manager is already initialized in init_auth
    # Configure login view settings
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # No need to define load_user here as it's already in auth.py
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(tracking_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(email_bp)
    app.register_blueprint(smtp_bp)
    
    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        """Handle 404 errors"""
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        """Handle 500 errors"""
        return render_template('errors/500.html'), 500
    
    # Create error templates directory if it doesn't exist
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
    
    # Create error templates during app initialization
    with app.app_context():
        create_error_templates()
    
    return app

# Create application instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
