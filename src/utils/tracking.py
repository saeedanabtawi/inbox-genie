import base64
import secrets
from datetime import datetime
from flask import make_response, redirect
from ..models import EmailHistory, db

def generate_tracking_token(email_id):
    """Generate a secure token for email tracking"""
    token_data = f"{email_id}:{secrets.token_hex(8)}"
    return base64.urlsafe_b64encode(token_data.encode()).decode()

def decode_tracking_token(token):
    """Decode the tracking token to extract email_id"""
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        email_id = int(decoded.split(':')[0])
        return email_id
    except (ValueError, IndexError):
        return None
