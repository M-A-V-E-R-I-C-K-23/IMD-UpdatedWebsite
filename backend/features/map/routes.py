import os
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, send_from_directory, current_app
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from core.config import (
    STATIONS, STATION_COORDS, MAHARASHTRA_CENTER, MAHARASHTRA_ZOOM,
    UPLOAD_FOLDER, ALLOWED_EXTENSIONS
)
from features.common.ocr import extract_text_from_image, generate_summary
from database import (
    add_news_item, get_news_items, delete_news_item,
    create_news_draft, publish_news,
    add_notice_item, get_notice_items, delete_notice_item,
    create_notice_draft, publish_notice,
    get_sigmet_status,
    add_dynamic_button, delete_dynamic_button, get_dynamic_buttons_by_section,
    track_admin_upload, get_admin_uploads, delete_admin_upload,
    get_employees, add_employee, update_employee, delete_employee,
    get_active_aerodrome_warnings
)
from .services import get_required_state_boundaries

map_bp = Blueprint('map', __name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@map_bp.route('/api/map/india_state')
def get_india_state():
    """Serve pre-compressed GeoJSON for performance"""
    accept_encoding = request.headers.get('Accept-Encoding', '')
    
    # Path handling
    # We need absolute path or relative to static folder
    # Assuming app root is backend/
    static_dir = os.path.join(current_app.root_path, '../frontend/static/geojson')
    
    if 'gzip' in accept_encoding and os.path.exists(os.path.join(static_dir, 'india_state.geojson.gz')):
        response = send_from_directory(static_dir, 'india_state.geojson.gz')
        response.headers['Content-Encoding'] = 'gzip'
        response.headers['Content-Type'] = 'application/geo+json'
        # content-length is set automatically by send_from_directory for the .gz file size
        return response
    
    return send_from_directory(static_dir, 'india_state.geojson')

@map_bp.route('/')
def index():
    """Landing page with Maharashtra map."""
    required_states, state_boundaries = get_required_state_boundaries()
    
    is_expanded = len(required_states) > 1 or "Maharashtra" not in required_states
    
    # Conditional Data Fetching
    admin_view = session.get('role') == 'admin'
    news_items = get_news_items(admin_view=admin_view)
    notice_items = get_notice_items(admin_view=admin_view)
    
    return render_template('map.html', 
                         stations=STATIONS, 
                         station_coords=STATION_COORDS,
                         required_states=list(required_states),
                         state_boundaries=state_boundaries,
                         is_expanded=is_expanded,
                         map_center=MAHARASHTRA_CENTER,
                         map_zoom=MAHARASHTRA_ZOOM,
                         news_items=news_items,
                         notice_items=notice_items,
                         dynamic_buttons=get_dynamic_buttons_by_section())

@map_bp.route('/head')
def head_profile():
    employees = get_employees()
    # Find employee with section 'HEAD' (case-insensitive)
    head = next((e for e in employees if e['section'] and e['section'].upper() == 'HEAD'), None)
    return render_template('head.html', head=head)

@map_bp.route('/employees')
def employee_list():
    all_employees = get_employees()
    # Filter out HEAD from the general list
    employees = [e for e in all_employees if not (e['section'] and e['section'].upper() == 'HEAD')]
    return render_template('employees.html', employees=employees)

@map_bp.route('/api/employees/add', methods=['POST'])
def add_employee_route():
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.json
    name = data.get('name')
    designation = data.get('designation')
    section = data.get('section')
    telephone = data.get('telephone')
    
    if not name:
        return jsonify({'success': False, 'error': 'Name is required'})
        
    if add_employee(name, designation, section, telephone, session.get('user')):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Database Error'})

@map_bp.route('/api/employees/update/<int:emp_id>', methods=['POST'])
def update_employee_route(emp_id):
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.json
    if update_employee(emp_id, data.get('name'), data.get('designation'), data.get('section'), data.get('telephone')):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Update Failed'})

@map_bp.route('/api/employees/delete/<int:emp_id>', methods=['POST'])
def delete_employee_route(emp_id):
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    if delete_employee(emp_id):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Delete Failed'})


# --- Auth Routes ---
@map_bp.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    success = False
    error = None
    
    if username == 'mwo_admin':
        if password == 'Admin@123':
            # 1. Prevent Session Fixation
            session.clear()
            
            # 2. Enable Persistent Session
            session.permanent = True
            
            # 3. Store Minimal User Info
            session['user'] = 'mwo_admin'
            session['role'] = 'admin'
            success = True
        else:
            error = "Invalid username or password"
    elif username:
        # Dev mode allows any other username without password
        # For non-admin dev users, we might not want permanent sessions, 
        # or we can treat them same for consistency in dev.
        # Assuming dev users are transient, but let's keep it simple.
        session.clear()
        session['user'] = username
        session['role'] = 'user'
        success = True
    else:
        error = "Invalid username or password"

    # Handle AJAX Requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if success:
            return jsonify({'success': True, 'redirect': url_for('map.index')})
        else:
            return jsonify({'success': False, 'error': error})

    # Legacy Fallback (Standard Form Submit)
    if success:
        return redirect(url_for('map.index'))
    else:
        # If standard submit fails, just redirect home for now (or could flash error)
        return redirect(url_for('map.index'))

@map_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('map.index'))

# --- Sigmet Route ---
@map_bp.route('/api/sigmet/status')
def get_sigmet_status_api():
    status = get_sigmet_status()
    if not status:
        return jsonify({"is_active": False, "count": 0, "message": "Initializing..."})
    return jsonify({
        "is_active": bool(status['is_active']),
        "count": status['count'],
        "phenomenon": status['phenomenon'],
        "valid_from": status['validity_text'],
        "last_checked": status['updated_at']
    })

# --- NEWS ROUTES ---

@map_bp.route('/api/news/upload', methods=['POST'])
def upload_news():
    if session.get('role') != 'admin':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
        
    try:
        title = request.form.get('title')
        description = request.form.get('description')
        file = request.files.get('file')
        
        if not file:
            return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400
            
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        # Backend File Type Detection
        file_type = 'document'
        if ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
            file_type = 'image'
        elif ext in ['pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'xls', 'xlsx']:
            file_type = 'document'
        else:
            file_type = 'other'
            
        subfolder = 'news'
        save_path = os.path.join(UPLOAD_FOLDER, subfolder, filename)
        file.save(save_path)
        
        upload_id = track_admin_upload(filename, file_type, f"{subfolder}/{filename}", session.get('user'))
    
        if add_news_item(title, description, filename, session.get('user'), upload_id):
            return jsonify({'status': 'success', 'message': 'News uploaded successfully'})
        else:
            return jsonify({'status': 'error', 'message': 'Database error'}), 500
            
    except Exception as e:
        logger.error(f"News Upload Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@map_bp.route('/api/news/draft', methods=['POST'])
def upload_news_draft():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    file = request.files.get('file')
    if not file: return jsonify({'success': False, 'error': 'No file'}), 400
    
    filename = secure_filename(f"NEWS_{int(datetime.utcnow().timestamp())}_{file.filename}")
    subfolder = 'news'
    path = os.path.join(UPLOAD_FOLDER, subfolder, filename)
    file.save(path)
    upload_id = track_admin_upload(filename, 'image', f"{subfolder}/{filename}", session.get('user'))
    
    # Process
    try:
        ocr_text = extract_text_from_image(path)
        summary = generate_summary(ocr_text)
        
        draft_id = create_news_draft(filename, ocr_text, summary, session.get('user'), upload_id)
        if draft_id:
            return jsonify({
                'success': True,
                'id': draft_id,
                'summary': summary,
                'ocr_text': ocr_text,
                'filename': filename
            })
    except Exception as e:
        logger.error(f"News Draft Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
        
    return jsonify({'success': False, 'error': 'Database Save Failed'}), 500

@map_bp.route('/api/news/publish/<int:item_id>', methods=['POST'])
def publish_news_route(item_id):
    if session.get('role') != 'admin': return jsonify({'error': 'Unauthorized'}), 403
    data = request.json
    if publish_news(item_id, data.get('title'), data.get('description')):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Update Failed'})

@map_bp.route('/api/news/delete/<int:item_id>', methods=['POST'])
def delete_news(item_id):
    if session.get('role') != 'admin': return jsonify({'error': 'Unauthorized'}), 403
    delete_news_item(item_id)
    return redirect(url_for('map.index'))

# --- NOTICES ROUTES ---

@map_bp.route('/api/notices/post', methods=['POST'])
def post_notice():
    if session.get('role') != 'admin':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
        
    try:
        title = request.form.get('title')
        message = request.form.get('message')
        file = request.files.get('file')
        
        filename = None
        upload_id = None
        
        if file:
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            
            # Backend File Type Detection
            file_type = 'document'
            if ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
                file_type = 'image'
            elif ext in ['pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'xls', 'xlsx']:
                file_type = 'document'
            else:
                file_type = 'other'

            subfolder = 'notices'
            save_path = os.path.join(UPLOAD_FOLDER, subfolder, filename)
            file.save(save_path)
            
            upload_id = track_admin_upload(filename, file_type, f"{subfolder}/{filename}", session.get('user'))
        
        if add_notice_item(title, message, filename, session.get('user'), upload_id):
            return jsonify({'status': 'success', 'message': 'Notice posted successfully'})
        else:
            return jsonify({'status': 'error', 'message': 'Database error'}), 500
            
    except Exception as e:
        logger.error(f"Notice Upload Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@map_bp.route('/api/notices/draft', methods=['POST'])
def upload_notice_draft():
    if session.get('role') != 'admin': return jsonify({'error': 'Unauthorized'}), 403
    file = request.files.get('file')
    if not file: return jsonify({'success': False, 'error': 'No file'}), 400
    
    filename = secure_filename(f"NOTICE_{int(datetime.utcnow().timestamp())}_{file.filename}")
    subfolder = 'notices'
    path = os.path.join(UPLOAD_FOLDER, subfolder, filename)
    file.save(path)
    upload_id = track_admin_upload(filename, 'image', f"{subfolder}/{filename}", session.get('user'))
    
    try:
        ocr_text = extract_text_from_image(path)
        summary = generate_summary(ocr_text)
        
        draft_id = create_notice_draft(filename, ocr_text, summary, session.get('user'), upload_id)
        if draft_id:
            return jsonify({
                'success': True,
                'id': draft_id,
                'summary': summary,
                'ocr_text': ocr_text,
                'filename': filename
            })
    except Exception as e:
        logger.error(f"Notice Draft Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'success': False, 'error': 'Failed'}), 500

@map_bp.route('/api/notices/publish/<int:item_id>', methods=['POST'])
def publish_notice_route(item_id):
    if session.get('role') != 'admin': return jsonify({'error': 'Unauthorized'}), 403
    data = request.json
    if publish_notice(item_id, data.get('title'), data.get('message')):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Update Failed'})

@map_bp.route('/api/notices/delete/<int:item_id>', methods=['POST'])
def delete_notice(item_id):
    if session.get('role') != 'admin': return jsonify({'error': 'Unauthorized'}), 403
    delete_notice_item(item_id)
    return redirect(url_for('map.index'))

@map_bp.route('/uploads/<type>/<filename>')
def serve_file(type, filename):
    if type not in ['news', 'notices', 'misc']: return "Invalid type", 400
    folder = os.path.join(UPLOAD_FOLDER, type)
    if type == 'misc' and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    return send_from_directory(folder, filename)

# --- AERODROME WARNING ROUTES ---

@map_bp.route('/api/warnings/active')
def get_active_warnings_api():
    """
    Get all active aerodrome warnings.
    """
    try:
        warnings = get_active_aerodrome_warnings()
        return jsonify({'success': True, 'data': warnings})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# --- Dynamic Button Management API ---

@map_bp.route('/api/buttons/add', methods=['POST'])
def add_button_api():
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    try:
        section = request.form.get('section')
        label = request.form.get('label')
        btn_type = request.form.get('type') # 'link' or 'file'
        url = request.form.get('url')
        file = request.files.get('file')
        
        if not section or not label or not btn_type:
             return jsonify({'success': False, 'error': 'Missing required fields'})

        file_path = None
        upload_id = None
        if btn_type == 'file' and file:
            filename = secure_filename(file.filename)
            # Use 'misc' folder for generic button files
            save_dir = os.path.join(UPLOAD_FOLDER, 'misc')
            os.makedirs(save_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{timestamp}_{filename}"
            file.save(os.path.join(save_dir, unique_filename))
            file_path = unique_filename
            
            # Track it
            upload_id = track_admin_upload(unique_filename, 'misc', f"misc/{unique_filename}", session.get('user'))
        
        add_dynamic_button(section, label, btn_type, url, file_path, upload_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@map_bp.route('/api/buttons/delete/<int:btn_id>', methods=['POST'])
def delete_button_api(btn_id):
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        # Decoupled deletion: Only delete the button entry, NOT the file.
        delete_dynamic_button(btn_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# --- ADMIN UPLOAD MANAGEMENT ---

@map_bp.route('/admin/uploads')
def admin_uploads_view():
    if session.get('role') != 'admin':
        return redirect(url_for('map.index')) # or 403
        
    uploads = get_admin_uploads(session.get('user'))
    return render_template('admin_uploads.html', uploads=uploads)

@map_bp.route('/admin/uploads/delete/<int:upload_id>', methods=['POST'])
def delete_admin_upload_route(upload_id):
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    try:
        file_path = delete_admin_upload(upload_id)
        if file_path:
            full_path = os.path.join(UPLOAD_FOLDER, file_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"Deleted admin upload: {full_path}")
            else:
                logger.warning(f"File not found on disk during delete: {full_path}")
                
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting upload: {e}")
        return jsonify({'success': False, 'error': str(e)})
