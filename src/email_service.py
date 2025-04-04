import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from datetime import datetime
from typing import Dict, List, Optional, Union, Tuple

class EmailService:
    """Service for handling email configuration and sending through SMTP"""
    
    @staticmethod
    def send_email(
        recipient_email: str,
        subject: str,
        html_content: str, 
        smtp_config: Dict,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[Dict]] = None
    ) -> Tuple[bool, str]:
        """
        Send an email using the provided SMTP configuration
        
        Args:
            recipient_email: Email address of the recipient
            subject: Email subject line
            html_content: HTML content of the email
            smtp_config: Dictionary containing SMTP configuration
            cc: List of CC email addresses
            bcc: List of BCC email addresses
            reply_to: Reply-to email address
            attachments: List of dictionaries containing attachment info
            
        Returns:
            Tuple containing success status (bool) and message (str)
        """
        try:
            # Extract SMTP settings from config
            sender_email = smtp_config.get('email')
            sender_name = smtp_config.get('name', '')
            server = smtp_config.get('server')
            port = int(smtp_config.get('port', 587))
            username = smtp_config.get('username')
            password = smtp_config.get('password')
            use_tls = smtp_config.get('use_tls', True)
            
            # Validate required SMTP settings
            if not all([sender_email, server, username, password]):
                return False, "Missing required SMTP settings"
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = formataddr((sender_name, sender_email))
            msg['To'] = recipient_email
            
            # Add CC recipients if provided
            if cc:
                msg['Cc'] = ', '.join(cc)
                
            # Add Reply-To if provided
            if reply_to:
                msg['Reply-To'] = reply_to
                
            # Add HTML content
            msg.attach(MIMEText(html_content, 'html'))
            
            # Get all recipients (for sending)
            recipients = [recipient_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)
            
            # Connect to SMTP server and send email
            if use_tls:
                context = ssl.create_default_context()
                with smtplib.SMTP(server, port) as smtp:
                    smtp.starttls(context=context)
                    smtp.login(username, password)
                    smtp.sendmail(sender_email, recipients, msg.as_string())
            else:
                with smtplib.SMTP(server, port) as smtp:
                    smtp.login(username, password)
                    smtp.sendmail(sender_email, recipients, msg.as_string())
                    
            return True, "Email sent successfully"
            
        except Exception as e:
            return False, f"Failed to send email: {str(e)}"
    
    @staticmethod
    def test_smtp_connection(smtp_config: Dict) -> Tuple[bool, str]:
        """
        Test SMTP server connection using the provided configuration
        
        Args:
            smtp_config: Dictionary containing SMTP configuration
            
        Returns:
            Tuple containing success status (bool) and message (str)
        """
        try:
            # Extract SMTP settings from config
            server = smtp_config.get('server')
            port = int(smtp_config.get('port', 587))
            username = smtp_config.get('username')
            password = smtp_config.get('password')
            use_tls = smtp_config.get('use_tls', True)
            
            # Validate required SMTP settings
            if not all([server, username, password]):
                return False, "Missing required SMTP settings"
            
            # Connect to SMTP server
            if use_tls:
                context = ssl.create_default_context()
                with smtplib.SMTP(server, port) as smtp:
                    smtp.starttls(context=context)
                    smtp.login(username, password)
            else:
                with smtplib.SMTP(server, port) as smtp:
                    smtp.login(username, password)
                    
            return True, "SMTP connection successful"
            
        except Exception as e:
            return False, f"Failed to connect to SMTP server: {str(e)}"
    
    @staticmethod
    def send_bulk_emails(
        recipients: List[Dict],
        subject_template: str,
        email_contents: List[str],
        smtp_config: Dict,
        delay_seconds: int = 2,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
    ) -> Dict:
        """
        Send bulk emails to multiple recipients
        
        Args:
            recipients: List of dictionaries containing recipient info
            subject_template: Email subject line template
            email_contents: List of HTML content for each email
            smtp_config: Dictionary containing SMTP configuration
            delay_seconds: Seconds to wait between emails (avoid rate limiting)
            cc: List of CC email addresses
            bcc: List of BCC email addresses
            reply_to: Reply-to email address
            
        Returns:
            Dictionary containing results of the bulk send operation
        """
        results = {
            "total": len(recipients),
            "successful": 0,
            "failed": 0,
            "errors": []
        }
        
        # Validate input arrays have matching lengths
        if len(recipients) != len(email_contents):
            results["errors"].append("Number of recipients does not match number of email contents")
            return results
        
        # Send each email
        for i, recipient in enumerate(recipients):
            recipient_email = recipient.get('email')
            if not recipient_email:
                results["failed"] += 1
                results["errors"].append(f"Missing email for recipient at index {i}")
                continue
                
            # Format subject with recipient data
            subject = subject_template
            for key, value in recipient.items():
                if isinstance(value, str):
                    subject = subject.replace(f"{{{key}}}", value)
            
            # Send the email
            success, message = EmailService.send_email(
                recipient_email=recipient_email,
                subject=subject,
                html_content=email_contents[i],
                smtp_config=smtp_config,
                cc=cc,
                bcc=bcc,
                reply_to=reply_to
            )
            
            if success:
                results["successful"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(f"Failed to send to {recipient_email}: {message}")
                
            # Add delay between sends to avoid rate limiting
            if i < len(recipients) - 1 and delay_seconds > 0:
                import time
                time.sleep(delay_seconds)
                
        return results
    
    @staticmethod
    def add_tracking_pixel(html_content: str, email_id: int, base_url: str) -> str:
        """
        Add tracking pixel to email HTML content
        
        Args:
            html_content: Original HTML content of email
            email_id: ID of the email in the database
            base_url: Base URL for tracking links (should include protocol and domain)
            
        Returns:
            HTML content with tracking pixel added
        """
        from app import generate_tracking_token
        
        # Generate tracking token for this email
        token = generate_tracking_token(email_id)
        
        # Create tracking pixel URL
        pixel_url = f"{base_url}/track/open/{token}.gif"
        
        # Add tracking pixel at the end of the email body
        tracking_pixel = f'<img src="{pixel_url}" width="1" height="1" alt="" style="display:none;border:0;width:1px;height:1px" />'
        
        # Insert the tracking pixel before the closing body tag
        if '</body>' in html_content:
            html_content = html_content.replace('</body>', f'{tracking_pixel}</body>')
        else:
            html_content = f'{html_content}{tracking_pixel}'
            
        return html_content
    
    @staticmethod
    def add_click_tracking(html_content: str, email_id: int, base_url: str) -> str:
        """
        Add click tracking to all links in the email
        
        Args:
            html_content: Original HTML content of email
            email_id: ID of the email in the database
            base_url: Base URL for tracking links
            
        Returns:
            HTML content with click tracking added to links
        """
        import re
        from app import generate_tracking_token
        
        # Generate tracking token for this email
        token = generate_tracking_token(email_id)
        
        # Find all links in the HTML
        link_pattern = re.compile(r'<a\s+(?:[^>]*?\s+)?href=(["\'])(.*?)\1', re.IGNORECASE)
        
        def replace_link(match):
            href = match.group(2)
            # Don't track unsubscribe or special links
            if 'unsubscribe' in href.lower() or 'mailto:' in href.lower():
                return match.group(0)
            
            # Create tracking URL with original URL as parameter
            tracking_url = f"{base_url}/track/click/{token}?url={href}"
            return match.group(0).replace(match.group(2), tracking_url)
        
        # Replace all links with tracking links
        tracked_html = link_pattern.sub(replace_link, html_content)
        
        return tracked_html
