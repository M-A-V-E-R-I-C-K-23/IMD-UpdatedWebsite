from flask import Blueprint, jsonify, request, session
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from core.extensions import logger
from core.config import UPLOAD_FOLDER
from database import (create_notam_draft, update_notam_status, update_notam_text, 
                     delete_notam, get_notams_by_status, get_public_active_notam)
from database import track_admin_upload
from .parser import parse_notam_pdf

notam_bp = Blueprint('notam', __name__)

@notam_bp.route('/api/notam/upload', methods=['POST'])
def upload_notam():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    file = request.files.get('file')
    if not file or file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
        
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'success': False, 'error': 'Only PDF files allowed'}), 400

    filename = secure_filename(f"NOTAM_{int(datetime.utcnow().timestamp())}.pdf")
    upload_path = os.path.join(UPLOAD_FOLDER, 'notams')
    os.makedirs(upload_path, exist_ok=True)
    filepath = os.path.join(upload_path, filename)
    
    try:
        file.save(filepath)
        upload_id = track_admin_upload(filename, 'pdf', f"notams/{filename}", session.get('user'))
        
        # Parse PDF
        result = parse_notam_pdf(filepath)
        
        if result['success']:
            # Save as DRAFT
            notam_id = create_notam_draft(
                filename, 
                result.get('raw_data', {}).get('raw_text', ''), # Parser doesn't return raw text, handled below
                result['formatted_text'],
                result['valid_until'],
                session.get('user'),
                upload_id
            )
            
            if notam_id:
                return jsonify({
                    'success': True, 
                    'id': notam_id,
                    'text': result['formatted_text'],
                    'status': 'DRAFT'
                })
            else:
                 return jsonify({'success': False, 'error': 'Database Save Failed'}), 500
        else:
            return jsonify({'success': False, 'error': 'Failed to parse PDF content'}), 500
            
    except Exception as e:
        logger.error(f"NOTAM Upload Error: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@notam_bp.route('/api/notam/list', methods=['GET'])
def list_notams():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    drafts = get_notams_by_status('DRAFT')
    active = get_notams_by_status('ACTIVE')
    archived = get_notams_by_status('ARCHIVED')
    
    return jsonify({
        'drafts': drafts,
        'active': active,
        'archived': archived
    })

@notam_bp.route('/api/notam/active')
def get_public_notam():
    # Public facing valid NOTAM
    notam = get_public_active_notam()
    if notam:
        return jsonify({
            'active': True,
            'text': notam['final_notam_text']
        })
    return jsonify({'active': False})

@notam_bp.route('/api/notam/publish/<int:notam_id>', methods=['POST'])
def publish_notam(notam_id):
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Logic: Archive any other active NOTAMs? Maybe not required if multiple valid supported.
    # For now, let's assume we can have multiple or business rule says 1.
    # User request doesn't specify limit, so just publish.
    
    if update_notam_status(notam_id, 'ACTIVE'):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Update Failed'})

@notam_bp.route('/api/notam/edit/<int:notam_id>', methods=['POST'])
def edit_notam(notam_id):
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.json
    new_text = data.get('text')
    new_date = data.get('valid_till')
    
    if not new_text:
         return jsonify({'success': False, 'error': 'No text provided'})

    if update_notam_text(notam_id, new_text, new_date):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Update Failed'})

@notam_bp.route('/api/notam/archive/<int:notam_id>', methods=['POST'])
def archive_notam(notam_id):
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    if update_notam_status(notam_id, 'ARCHIVED'):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Update Failed'})

@notam_bp.route('/api/notam/delete/<int:notam_id>', methods=['POST'])
def delete_notam_route(notam_id):
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    if delete_notam(notam_id):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Database Error'}), 500

@notam_bp.route('/api/notam/generate', methods=['POST'])
def generate_notam_text():
    """
    Parses a PDF and returns the text WITHOUT saving to DB.
    For manual copy/verification.
    """
    file = request.files.get('file')
    if not file or file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
        
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'success': False, 'error': 'Only PDF files allowed'}), 400

    filename = secure_filename(f"TEMP_NOTAM_{int(datetime.utcnow().timestamp())}_{file.filename}")
    upload_path = os.path.join(UPLOAD_FOLDER, 'temp')
    os.makedirs(upload_path, exist_ok=True)
    filepath = os.path.join(upload_path, filename)
    
    try:
        file.save(filepath)
        result = parse_notam_pdf(filepath)
        try: os.remove(filepath)
        except: pass
            
        if result['success']:
            return jsonify({
                'success': True, 
                'text': result['formatted_text']
            })
        else:
            return jsonify({'success': False, 'error': result.get('error', 'Unknown parsing error')})
            
    except Exception as e:
        logger.error(f"NOTAM Gen Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
