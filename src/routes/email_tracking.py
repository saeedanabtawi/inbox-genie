from flask import Blueprint, make_response, redirect, request
from datetime import datetime
from ..models import EmailHistory, db
from ..utils.tracking import decode_tracking_token

tracking_bp = Blueprint('tracking', __name__, url_prefix='/track')

@tracking_bp.route('/open/<token>.gif')
def track_open(token):
    """Track email opens via a transparent tracking pixel"""
    email_id = decode_tracking_token(token)
    
    if email_id:
        email = EmailHistory.query.get(email_id)
        if email and not email.opened:
            email.opened = True
            email.opened_at = datetime.utcnow()
            db.session.commit()
    
    # Return a transparent 1x1 pixel GIF
    transparent_pixel = b'R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'
    response = make_response(transparent_pixel)
    response.headers.set('Content-Type', 'image/gif')
    response.headers.set('Cache-Control', 'no-cache, no-store, must-revalidate')
    return response

@tracking_bp.route('/click/<token>')
def track_click(token):
    """Track email link clicks"""
    email_id = decode_tracking_token(token)
    redirect_url = request.args.get('url', '/')
    
    if email_id:
        email = EmailHistory.query.get(email_id)
        if email and not email.clicked:
            email.clicked = True
            email.clicked_at = datetime.utcnow()
            db.session.commit()
    
    return redirect(redirect_url)
