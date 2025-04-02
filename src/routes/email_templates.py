from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from ..models import EmailTemplate, db
from ..utils.email_generator import EmailGenerator

templates_bp = Blueprint('templates', __name__, url_prefix='/templates')

@templates_bp.route('/')
@login_required
def manage_templates():
    """Render the template management page"""
    # Load user's custom templates from the database
    custom_templates = EmailTemplate.query.filter_by(user_id=current_user.id).all()
    
    return render_template(
        'template_management.html', 
        custom_templates=custom_templates
    )

@templates_bp.route('/save-template', methods=['POST'])
@login_required
def save_template():
    """Save a customized email template"""
    data = request.json
    template_type = data.get('template_type')
    template_content = data.get('template_content')
    
    if not template_type or not template_content:
        return jsonify({'success': False, 'message': 'Template type and content are required'})
    
    try:
        # Check if this user already has a customized version of this default template
        existing_template = EmailTemplate.query.filter_by(
            user_id=current_user.id, 
            template_type=template_type
        ).first()
        
        if existing_template:
            # Update existing template
            existing_template.content = template_content
            existing_template.updated_at = datetime.now()
            db.session.commit()
            message = f'Template "{template_type}" updated successfully'
        else:
            # Create new template based on default
            new_template = EmailTemplate(
                user_id=current_user.id,
                name=template_type.replace('_', ' ').title(),
                description=f'Customized {template_type.replace("_", " ")} template',
                content=template_content,
                template_type=template_type,
                required_fields='name,company,role,email'
            )
            db.session.add(new_template)
            db.session.commit()
            message = f'Template "{template_type}" customized successfully'
        
        return jsonify({'success': True, 'message': message})
    
    except Exception as e:
        db.session.rollback()
        print(f"Error saving template: {str(e)}")
        return jsonify({'success': False, 'message': f'Error saving template: {str(e)}'}), 500

@templates_bp.route('/save-custom-template', methods=['POST'])
@login_required
def save_custom_template():
    """Save a new custom template"""
    data = request.json
    template_name = data.get('template_name')
    template_content = data.get('template_content')
    template_description = data.get('template_description', '')
    required_fields = data.get('required_fields', 'name,company,role,email')
    
    # Validate inputs
    if not template_name or not template_content:
        return jsonify({'success': False, 'message': 'Template name and content are required'})
    
    try:
        # Check if a template with this name already exists for this user
        existing_template = EmailTemplate.query.filter_by(
            user_id=current_user.id, 
            name=template_name
        ).first()
        
        if existing_template:
            # Update existing template
            existing_template.content = template_content
            existing_template.description = template_description
            existing_template.required_fields = required_fields
            existing_template.updated_at = datetime.now()
            db.session.commit()
            return jsonify({
                'success': True, 
                'message': f'Template "{template_name}" updated successfully',
                'template_id': existing_template.id
            })
        else:
            # Create new template
            new_template = EmailTemplate(
                user_id=current_user.id,
                name=template_name,
                description=template_description,
                content=template_content,
                template_type='custom',
                required_fields=required_fields
            )
            db.session.add(new_template)
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'message': f'Custom template "{template_name}" created successfully',
                'template_id': new_template.id
            })
    
    except Exception as e:
        db.session.rollback()
        print(f"Error saving template: {str(e)}")
        return jsonify({'success': False, 'message': f'Error saving template: {str(e)}'}), 500

@templates_bp.route('/delete/<int:template_id>', methods=['POST'])
@login_required
def delete_template(template_id):
    """Delete a custom email template"""
    try:
        # Find the template in the database
        template = EmailTemplate.query.filter_by(id=template_id, user_id=current_user.id).first()
        
        if not template:
            return jsonify({
                'success': False,
                'message': 'Template not found or you do not have permission to delete it'
            }), 404
        
        # Get template name for the success message
        template_name = template.name
        
        # Delete the template
        db.session.delete(template)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Template "{template_name}" deleted successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting template: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error deleting template: {str(e)}'
        }), 500

@templates_bp.route('/api/all', methods=['GET'])
@login_required
def get_all_templates():
    """API endpoint to get all available email templates (default and custom)"""
    try:
        # Get default templates
        default_templates = [
            {
                'id': 'default_cold_email',
                'name': 'Cold Email',
                'type': 'default',
                'description': 'Default template for cold outreach',
                'content': EmailGenerator.get_default_template('cold_email')
            },
            {
                'id': 'default_follow_up',
                'name': 'Follow Up',
                'type': 'default',
                'description': 'Default template for following up with prospects',
                'content': EmailGenerator.get_default_template('follow_up')
            },
            {
                'id': 'default_meeting_request',
                'name': 'Meeting Request',
                'type': 'default',
                'description': 'Default template for requesting meetings',
                'content': EmailGenerator.get_default_template('meeting_request')
            }
        ]
        
        # Get user's custom templates from database
        custom_templates = EmailTemplate.query.filter_by(user_id=current_user.id).all()
        
        # Convert to list of dictionaries
        custom_templates_list = []
        for template in custom_templates:
            custom_templates_list.append({
                'id': template.id,
                'name': template.name,
                'type': 'custom',
                'description': template.description,
                'content': template.content,
                'required_fields': template.required_fields.split(',')
            })
        
        # Combine all templates
        all_templates = default_templates + custom_templates_list
        
        return jsonify({
            'success': True,
            'templates': all_templates
        })
    
    except Exception as e:
        print(f"Error retrieving templates: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@templates_bp.route('/api/<template_id>', methods=['GET'])
@login_required
def get_template(template_id):
    """API endpoint to get a specific email template"""
    try:
        if template_id.startswith('default_'):
            # Return a default template
            template_type = template_id.replace('default_', '')
            template_content = EmailGenerator.get_default_template(template_type)
            
            return jsonify({
                'success': True,
                'template': {
                    'id': template_id,
                    'name': template_type.replace('_', ' ').title(),
                    'type': 'default',
                    'content': template_content,
                    'required_fields': ['name', 'company', 'role', 'email']
                }
            })
        else:
            # Fetch custom template from database
            try:
                template_id_int = int(template_id)
                template = EmailTemplate.query.filter_by(id=template_id_int, user_id=current_user.id).first()
                
                if not template:
                    return jsonify({
                        'success': False,
                        'error': 'Template not found'
                    }), 404
                
                return jsonify({
                    'success': True,
                    'template': {
                        'id': template.id,
                        'name': template.name,
                        'type': 'custom',
                        'description': template.description,
                        'content': template.content,
                        'required_fields': template.required_fields.split(',')
                    }
                })
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid template ID'
                }), 400
    
    except Exception as e:
        print(f"Error retrieving template: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
