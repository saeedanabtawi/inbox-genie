import io
import csv
from flask_login import current_user
from datetime import datetime
from ..models import EmailHistory, db

class EmailGenerator:
    @staticmethod
    def generate_email(recipient_data, template_type='cold_email'):
        """
        Generate a personalized cold email based on recipient data
        
        Args:
            recipient_data (dict): Dictionary containing recipient information
            template_type (str): Type of email template to use
            
        Returns:
            str: Personalized email content
        """
        # Extract recipient data
        name = recipient_data.get('name', 'Prospect')
        role = recipient_data.get('role', 'Professional')
        company = recipient_data.get('company', 'Company')
        industry = recipient_data.get('industry', 'your industry')
        recent_activity = recipient_data.get('recent_activity', '')
        industry_news = recipient_data.get('industry_news', '')
        pain_points = recipient_data.get('pain_points', '')
        email = recipient_data.get('email', '')
        
        # Generate a personalized opening based on available information
        if recent_activity:
            opening = f"I recently came across your {recent_activity} and was impressed by your work at {company}."
        elif industry_news:
            opening = f"I noticed the recent news about {industry_news} in the {industry} sector and thought of {company}."
        else:
            opening = f"I hope this email finds you well. I noticed your role as {role} at {company} and thought I'd reach out."
        
        # Generate a value proposition based on pain points
        if pain_points:
            value_prop = f"Many {role}s in {industry} face challenges with {pain_points}. Our solution has helped similar companies increase efficiency by 30% and reduce costs significantly."
        else:
            value_prop = f"Our solution has helped many companies in {industry} increase efficiency by 30% and reduce costs significantly."
        
        # Construct the full email
        if template_type == 'cold_email':
            email = f"""Subject: Quick Question About {company}'s Approach to Growth

Hi {name},

{opening}

{value_prop}

I'd love to share how we've helped other {industry} companies achieve similar results. Would you be open to a brief 15-minute call next week to explore if there might be a fit?

Looking forward to your response,

{current_user.username if current_user.is_authenticated else '[Your Name]'}
[Your Position]
[Your Company]
[Your Contact Information]"""
        elif template_type == 'follow_up':
            email = f"""Hi {name},

I wanted to follow up on my previous email regarding how we can help {company} with {pain_points}. Have you had a chance to consider my proposal?

I'm available to discuss how our solution has helped companies like yours improve their results by 30% on average.

Let me know if you have 15 minutes this week for a quick call.

Best regards,
{current_user.username if current_user.is_authenticated else '[Your Name]'}
[Your Position]
[Your Company]
[Your Contact Information]"""
        elif template_type == 'meeting_request':
            email = f"""Hi {name},

I'd like to schedule a brief 15-minute call to discuss how our solution can help {company} address {pain_points}.

Are you available next Tuesday or Wednesday afternoon?

Looking forward to connecting!

Best regards,
{current_user.username if current_user.is_authenticated else '[Your Name]'}
[Your Position]
[Your Company]
[Your Contact Information]"""
        else:
            email = f"""Subject: Quick Question About {company}'s Approach to Growth

Hi {name},

{opening}

{value_prop}

I'd love to share how we've helped other {industry} companies achieve similar results. Would you be open to a brief 15-minute call next week to explore if there might be a fit?

Looking forward to your response,

{current_user.username if current_user.is_authenticated else '[Your Name]'}
[Your Position]
[Your Company]
[Your Contact Information]"""
        
        return email
    
    @staticmethod
    def get_default_template(template_type='cold_email'):
        """
        Get the default email template
        
        Args:
            template_type (str): Type of email template to use
            
        Returns:
            str: Default email template
        """
        if template_type == 'cold_email':
            return """Subject: Quick Question About {{company}}'s Approach to Growth

Hi {{name}},

I hope this email finds you well. I noticed your role as {{role}} at {{company}} and thought I'd reach out.

Many {{role}}s in {{industry}} face challenges with {{pain_points}}. Our solution has helped similar companies increase efficiency by 30% and reduce costs significantly.

I'd love to share how we've helped other {{industry}} companies achieve similar results. Would you be open to a brief 15-minute call next week to explore if there might be a fit?

Looking forward to your response,

{{username}}
{{position}}
{{company}}
{{contact_info}}"""
        elif template_type == 'follow_up':
            return """Hi {{name}},

I wanted to follow up on my previous email regarding how we can help {{company}} with {{pain_points}}. Have you had a chance to consider my proposal?

I'm available to discuss how our solution has helped companies like yours improve their results by 30% on average.

Let me know if you have 15 minutes this week for a quick call.

Best regards,
{{username}}
{{position}}
{{company}}
{{contact_info}}"""
        elif template_type == 'meeting_request':
            return """Hi {{name}},

I'd like to schedule a brief 15-minute call to discuss how our solution can help {{company}} address {{pain_points}}.

Are you available next Tuesday or Wednesday afternoon?

Looking forward to connecting!

Best regards,
{{username}}
{{position}}
{{company}}
{{contact_info}}"""
        else:
            return """Subject: Quick Question About {{company}}'s Approach to Growth

Hi {{name}},

I hope this email finds you well. I noticed your role as {{role}} at {{company}} and thought I'd reach out.

Many {{role}}s in {{industry}} face challenges with {{pain_points}}. Our solution has helped similar companies increase efficiency by 30% and reduce costs significantly.

I'd love to share how we've helped other {{industry}} companies achieve similar results. Would you be open to a brief 15-minute call next week to explore if there might be a fit?

Looking forward to your response,

{{username}}
{{position}}
{{company}}
{{contact_info}}"""
    
    @staticmethod
    def generate_email_from_template(recipient_data, template_content):
        """
        Generate a personalized email from a template
        
        Args:
            recipient_data (dict): Dictionary containing recipient information
            template_content (str): Email template content
            
        Returns:
            str: Personalized email content
        """
        # Replace placeholders in the template
        email = template_content.replace('{{name}}', recipient_data.get('name', 'Prospect'))
        email = email.replace('{{company}}', recipient_data.get('company', 'Company'))
        email = email.replace('{{role}}', recipient_data.get('role', 'Professional'))
        email = email.replace('{{industry}}', recipient_data.get('industry', 'your industry'))
        email = email.replace('{{pain_points}}', recipient_data.get('pain_points', ''))
        email = email.replace('{{username}}', current_user.username if current_user.is_authenticated else '[Your Name]')
        email = email.replace('{{position}}', '[Your Position]')
        email = email.replace('{{company}}', '[Your Company]')
        email = email.replace('{{contact_info}}', '[Your Contact Information]')
        
        return email
    
    @staticmethod
    def process_csv_data(csv_data, template_type='cold_email'):
        """Process CSV data and generate emails for each recipient
        
        Args:
            csv_data (str): CSV data as a string
            template_type (str): Type of email template to use
            
        Returns:
            dict: Dictionary containing generated emails and validation results
        """
        result = {
            'success': True,
            'emails': [],
            'errors': [],
            'total_recipients': 0,
            'successful_recipients': 0
        }
        
        try:
            # Parse CSV data
            csv_file = io.StringIO(csv_data)
            csv_reader = csv.DictReader(csv_file)
            
            # Get headers from CSV
            headers = csv_reader.fieldnames
            
            # Validate required fields
            required_fields = ['name', 'role', 'company', 'email']
            missing_fields = [field for field in required_fields if field.lower() not in [h.lower() for h in headers]]
            
            if missing_fields:
                result['success'] = False
                result['errors'].append(f"Missing required columns: {', '.join(missing_fields)}")
                return result
            
            # Process each row
            for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 to account for header row
                result['total_recipients'] += 1
                
                # Normalize header names to lowercase and create a standardized row dictionary
                standardized_row = {}
                for header in headers:
                    key = header.lower().strip()
                    standardized_row[key] = row[header].strip() if row[header] else ''
                
                # Validate required fields in each row
                row_errors = []
                for field in required_fields:
                    if not standardized_row.get(field):
                        row_errors.append(f"Missing {field}")
                        
                if row_errors:
                    result['errors'].append(f"Row {row_num}: {', '.join(row_errors)}")
                    continue
                
                try:
                    # Generate email for this recipient
                    email = EmailGenerator.generate_email(standardized_row, template_type)
                    result['emails'].append({
                        'recipient': standardized_row,
                        'email': email
                    })
                    result['successful_recipients'] += 1
                except Exception as e:
                    result['errors'].append(f"Row {row_num}: Failed to generate email: {str(e)}")
                    
            # Update success flag if we have any emails
            if result['successful_recipients'] == 0 and result['total_recipients'] > 0:
                result['success'] = False
                
            return result
            
        except Exception as e:
            result['success'] = False
            result['errors'].append(f"Error processing CSV: {str(e)}")
            return result
