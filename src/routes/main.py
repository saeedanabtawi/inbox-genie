from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime, date, timedelta
from ..models import EmailHistory, EmailTemplate, SMTPConfig, db
from ..utils.email_generator import EmailGenerator
from ..email_service import EmailService

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def landing():
    """Render the landing page - public access"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('landing.html')

# Add a home alias for backward compatibility
@main_bp.route('/home')
def home():
    """Alias for landing page to maintain backward compatibility"""
    return landing()

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Render the dashboard page with analytics data"""
    try:
        # Count emails sent by the current user
        emails_count = EmailHistory.query.filter_by(user_id=current_user.id).count()
        
        # Count unique bulk campaigns
        campaigns_count = db.session.query(func.count(func.distinct(EmailHistory.campaign_name))).filter(
            EmailHistory.user_id == current_user.id,
            EmailHistory.campaign_name.isnot(None)
        ).scalar() or 0
        
        # Calculate open and click rates from real data
        campaign_stats = []
        
        # Get all campaigns for the user
        campaigns = db.session.query(EmailHistory.campaign_name).filter(
            EmailHistory.user_id == current_user.id,
            EmailHistory.campaign_name.isnot(None)
        ).distinct().all()
        
        # Average score placeholders (we'll calculate better metrics later)
        avg_score = 8.7  
        
        # Calculate metrics for each campaign
        for campaign in campaigns:
            campaign_name = campaign[0]
            campaign_emails = EmailHistory.query.filter_by(
                user_id=current_user.id,
                campaign_name=campaign_name
            ).all()
            
            total_emails = len(campaign_emails)
            opened_emails = sum(1 for email in campaign_emails if email.opened)
            clicked_emails = sum(1 for email in campaign_emails if email.clicked)
            
            # Calculate rates
            open_rate = round((opened_emails / total_emails) * 100) if total_emails > 0 else 0
            click_rate = round((clicked_emails / total_emails) * 100) if total_emails > 0 else 0
            reply_rate = round(click_rate * 0.6)  # Placeholder: estimate reply rate from click rate
            
            latest_email = max(campaign_emails, key=lambda x: x.sent_at) if campaign_emails else None
            
            campaign_stats.append({
                'name': campaign_name,
                'type': 'Email Campaign',
                'emails_sent': total_emails,
                'date': latest_email.sent_at.strftime('%b %d, %Y') if latest_email else 'Unknown',
                'open_rate': open_rate,
                'click_rate': click_rate,
                'reply_rate': reply_rate,
                'status': 'Active' if latest_email and (datetime.utcnow() - latest_email.sent_at).days < 7 else 'Completed'
            })
        
        # Add demo data if no campaigns exist
        if not campaign_stats:
            campaign_stats = [
                {
                    'name': 'No campaigns yet',
                    'type': 'N/A',
                    'emails_sent': 0,
                    'date': datetime.now().strftime('%b %d, %Y'),
                    'open_rate': 0,
                    'click_rate': 0,
                    'reply_rate': 0,
                    'status': 'N/A'
                }
            ]
        
        # Calculate usage percentage based on subscription tier limits
        max_emails = 500  # Default for premium
        if current_user.subscription_tier == 'Basic':
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
        campaign_stats = []
    
    # Get recent activity
    recent_activity = []
    recent_emails = EmailHistory.query.filter_by(user_id=current_user.id).order_by(EmailHistory.sent_at.desc()).limit(5).all()
    
    for email in recent_emails:
        time_diff = datetime.utcnow() - email.sent_at
        if time_diff.days > 0:
            time_ago = f"{time_diff.days} days ago"
        elif time_diff.seconds >= 3600:
            time_ago = f"{time_diff.seconds // 3600} hours ago"
        else:
            time_ago = f"{time_diff.seconds // 60} minutes ago"
            
        activity_type = "campaign" if email.campaign_name else "email"
        activity = {
            'type': activity_type,
            'title': f"{'Bulk Email' if email.campaign_name else 'Email'} sent to {email.recipient}",
            'description': f"Subject: {email.subject}",
            'time': time_ago
        }
        recent_activity.append(activity)
    
    # Create the analytics object
    analytics = {
        'user_stats': {
            'emails_generated': emails_count,
            'bulk_campaigns': campaigns_count,
            'avg_score': avg_score,
            'usage_percentage': usage_percentage
        },
        'campaigns': campaign_stats,
        'recent_activity': recent_activity
    }
    
    return render_template('dashboard.html', analytics=analytics)

@main_bp.route('/pricing')
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

@main_bp.route('/about')
def about_page():
    """Render the About Us page."""
    return render_template('main/about.html', title="About Us")

@main_bp.route('/careers')
def careers_page():
    """Render the Careers page."""
    return render_template('main/careers.html', title="Careers")

@main_bp.route('/contact')
def contact_page():
    """Render the Contact Us page."""
    # Add logic here to handle form submission if implementing a functional contact form
    return render_template('main/contact.html', title="Contact Us")

@main_bp.route('/privacy')
def privacy_page():
    """Render the Privacy Policy page."""
    current_date = date.today().strftime("%B %d, %Y")
    return render_template('main/privacy.html', title="Privacy Policy", current_date=current_date)

@main_bp.route('/terms')
def terms_page():
    """Render the Terms of Service page."""
    current_date = date.today().strftime("%B %d, %Y")
    return render_template('main/terms.html', title="Terms of Service", current_date=current_date)
