from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
import datetime as dt
from datetime import datetime
from ..models import db

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

@profile_bp.route('/')
@login_required
def view_profile():
    """Render the user profile page"""
    # In a real application, you might fetch user statistics from a database
    stats = {
        'emails_generated': 0,
        'bulk_campaigns': 0,
        'avg_score': 'N/A'
    }
    return render_template('profile.html', stats=stats)

@profile_bp.route('/update', methods=['POST'])
@login_required
def update_profile():
    """Handle profile update form submission"""
    if request.method == 'POST':
        # In a real app, you would validate and update the user profile
        flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile.view_profile'))

@profile_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Handle password change form submission"""
    if request.method == 'POST':
        # In a real app, you would validate passwords and update them
        flash('Password changed successfully!', 'success')
    return redirect(url_for('profile.view_profile'))

@profile_bp.route('/subscription')
@login_required
def subscription():
    """Render the subscription management page"""
    # In a real app, these would be fetched from the database
    custom_templates_count = 5  # Example count
    
    # Reuse the plans data from the pricing page
    plans = {
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

@profile_bp.route('/upgrade-subscription', methods=['POST'])
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
            
    return redirect(url_for('profile.subscription'))

@profile_bp.route('/update-billing-cycle', methods=['POST'])
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
        
    return redirect(url_for('profile.subscription'))

@profile_bp.route('/downgrade-to-free', methods=['POST'])
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
        
    return redirect(url_for('profile.subscription'))
