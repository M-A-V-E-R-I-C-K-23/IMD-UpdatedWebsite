import os
from flask import Blueprint, render_template, request, jsonify, session, send_from_directory, current_app, redirect, url_for
from werkzeug.utils import secure_filename
from core.config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS, STATIONS
from datetime import datetime
from database.operations import track_admin_upload, delete_admin_upload_by_path

documents_bp = Blueprint('documents', __name__)

# Map module types to folder names
MODULE_FOLDERS = {
    'sop': 'sop',
    'circulars': 'circulars',
    'workshops': 'workshops'
}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_icon(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext == 'pdf': return '📄'
    if ext in ['doc', 'docx']: return '📝'
    if ext in ['xls', 'xlsx']: return '📊'
    if ext in ['jpg', 'jpeg', 'png']: return '🖼️'
    return '📁'

@documents_bp.route('/documents/<module_type>/<section>')
def list_documents(module_type, section):
    if module_type not in MODULE_FOLDERS:
        return "Invalid module", 404
        
    folder_name = MODULE_FOLDERS[module_type]
    # Structure: uploads/sop/aviation or uploads/circulars/admin
    target_dir = os.path.join(UPLOAD_FOLDER, folder_name, section)
    os.makedirs(target_dir, exist_ok=True)
    
    files = []
    try:
        for f in os.listdir(target_dir):
            if not f.startswith('.'):
                file_path = os.path.join(target_dir, f)
                stats = os.stat(file_path)
                files.append({
                    'name': f,
                    'size': f"{stats.st_size / 1024:.1f} KB",
                    'date': datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M'),
                    'icon': get_file_icon(f),
                    'type': module_type,
                    'section': section
                })
    except Exception as e:
        current_app.logger.error(f"Error listing files: {e}")
        
    # Sort by date descending
    files.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('documents.html', 
                         files=files, 
                         module_type=module_type, 
                         section=section,
                         title=f"{module_type.upper()} - {section.title()}",
                         stations=STATIONS,
                         default_station="VABB")

@documents_bp.route('/api/documents/upload/<module_type>/<section>', methods=['POST'])
def upload_document(module_type, section):
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    if module_type not in MODULE_FOLDERS:
        return jsonify({'success': False, 'error': 'Invalid module'}), 400
        
    file = request.files.get('file')
    if not file or not file.filename:
        return jsonify({'success': False, 'error': 'No file selected'}), 400
        
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
    try:
        folder_name = MODULE_FOLDERS[module_type]
        target_dir = os.path.join(UPLOAD_FOLDER, folder_name, section)
        os.makedirs(target_dir, exist_ok=True)
        
        filename = secure_filename(file.filename)
        # Add timestamp to avoid collisions
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_name = f"{timestamp}_{filename}"
        
        file.save(os.path.join(target_dir, save_name))
        
        # Track upload in DB for "My Uploads"
        relative_path = f"{folder_name}/{section}/{save_name}"
        track_admin_upload(filename, module_type, relative_path, session.get('user'))
        
        return jsonify({'success': True, 'message': 'File uploaded successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Upload error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@documents_bp.route('/api/documents/serve/<module_type>/<section>/<filename>')
def serve_document(module_type, section, filename):
    if module_type not in MODULE_FOLDERS:
        return "Invalid module", 404
        
    folder_name = MODULE_FOLDERS[module_type]
    target_dir = os.path.join(UPLOAD_FOLDER, folder_name, section)
    return send_from_directory(target_dir, filename)

@documents_bp.route('/api/documents/delete/<module_type>/<section>/<filename>', methods=['POST'])
def delete_document(module_type, section, filename):
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    if module_type not in MODULE_FOLDERS:
        return jsonify({'success': False, 'error': 'Invalid module'}), 400
        
    try:
        folder_name = MODULE_FOLDERS[module_type]
        target_dir = os.path.join(UPLOAD_FOLDER, folder_name, section)
        file_path = os.path.join(target_dir, filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            
            # Also remove from DB so it disappears from "My Uploads" UI
            relative_path = f"{folder_name}/{section}/{filename}"
            delete_admin_upload_by_path(relative_path)
            
            return jsonify({'success': True, 'message': 'File deleted'})
        return jsonify({'success': False, 'error': 'File not found'}), 404
        
    except Exception as e:
        current_app.logger.error(f"Delete error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
