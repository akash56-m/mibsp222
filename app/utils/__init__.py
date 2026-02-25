"""
MIBSP Utility Modules
Helper functions for audit logging, tracking ID generation, and file handling.
"""
import os
import uuid
import secrets
import string
from datetime import datetime
from functools import wraps
from flask import session, redirect, url_for, flash, request, current_app
from werkzeug.utils import secure_filename

from app import db
from app.models import AuditLog


# =============================================================================
# DECORATORS - Role-Based Access Control
# =============================================================================

def login_required(f):
    """Decorator to require user login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('public.index'))
        return f(*args, **kwargs)
    return decorated_function


def officer_required(f):
    """Decorator to require officer or admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if session.get('role') not in ['officer', 'admin']:
            flash('Officer access required.', 'danger')
            return redirect(url_for('public.index'))
        return f(*args, **kwargs)
    return decorated_function


# =============================================================================
# TRACKING ID GENERATOR
# =============================================================================

def generate_tracking_id():
    """
    Generate a unique tamper-proof tracking ID.
    Format: MIB + 8 random uppercase alphanumeric characters
    Example: MIB3A9F2K1
    
    Ensures uniqueness by checking database.
    """
    from app.models import Complaint
    
    prefix = 'MIB'
    attempts = 0
    max_attempts = 100
    
    while attempts < max_attempts:
        # Generate 8 random uppercase alphanumeric characters
        random_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) 
                              for _ in range(8))
        tracking_id = f"{prefix}{random_part}"
        
        # Check if already exists
        existing = Complaint.query.filter_by(tracking_id=tracking_id).first()
        if not existing:
            return tracking_id
        
        attempts += 1
    
    # Fallback: add timestamp for uniqueness
    timestamp = datetime.utcnow().strftime('%H%M%S')
    random_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) 
                          for _ in range(2))
    return f"{prefix}{timestamp}{random_part}"


# =============================================================================
# FILE UPLOAD HANDLER
# =============================================================================

def allowed_file(filename):
    """Check if file extension is allowed."""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in current_app.config['ALLOWED_EXTENSIONS']


def get_file_extension(filename):
    """Safely extract file extension."""
    if '.' not in filename:
        return ''
    return filename.rsplit('.', 1)[1].lower()


def save_uploaded_file(file, subfolder='evidence'):
    """
    Securely save an uploaded file with UUID prefix.
    
    Args:
        file: Flask FileStorage object
        subfolder: Subdirectory within uploads
    
    Returns:
        tuple: (success: bool, result: str) - result is filename or error message
    """
    if not file or file.filename == '':
        return False, 'No file selected'
    
    if not allowed_file(file.filename):
        allowed = ', '.join(current_app.config['ALLOWED_EXTENSIONS'])
        return False, f'Invalid file type. Allowed: {allowed}'
    
    # Generate secure filename with UUID prefix
    original_filename = secure_filename(file.filename)
    file_ext = get_file_extension(original_filename)
    unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
    
    # Create subfolder if needed
    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(upload_path, exist_ok=True)
    
    # Full path for saving
    file_path = os.path.join(upload_path, unique_filename)
    
    try:
        file.save(file_path)
        # Store relative path in database
        relative_path = os.path.join(subfolder, unique_filename)
        return True, relative_path
    except Exception as e:
        current_app.logger.error(f'File upload error: {str(e)}')
        return False, 'Error saving file. Please try again.'


def delete_uploaded_file(relative_path):
    """
    Delete an uploaded file.
    
    Args:
        relative_path: Path relative to UPLOAD_FOLDER
    
    Returns:
        bool: True if deleted or not found, False on error
    """
    if not relative_path:
        return True
    
    full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], relative_path)
    
    try:
        if os.path.exists(full_path):
            os.remove(full_path)
        return True
    except Exception as e:
        current_app.logger.error(f'File deletion error: {str(e)}')
        return False


# =============================================================================
# AUDIT LOG HELPER
# =============================================================================

def log_action(action, details=None, user=None):
    """
    Create an audit log entry.
    
    Args:
        action: Short description of action (e.g., 'LOGIN', 'STATUS_UPDATE')
        details: Additional details (JSON-serializable)
        user: User object (optional, uses session if not provided)
    """
    # Get user info
    if user is None:
        user_id = session.get('user_id')
        username = session.get('username', 'anonymous')
        role = session.get('role', 'guest')
    else:
        user_id = user.id
        username = user.username
        role = user.role
    
    # Get IP address
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_address and ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()
    
    # Convert details to string if needed
    if details and not isinstance(details, str):
        import json
        try:
            details = json.dumps(details)
        except:
            details = str(details)
    
    # Create audit log entry
    AuditLog.create_entry(
        user_id=user_id,
        username=username,
        role=role,
        action=action,
        details=details,
        ip_address=ip_address
    )


# =============================================================================
# FORMATTING HELPERS
# =============================================================================

def format_status_badge(status):
    """Return Bootstrap badge class for status."""
    badges = {
        'Pending': 'bg-warning text-dark',
        'Under Review': 'bg-info text-dark',
        'Action Taken': 'bg-primary',
        'Closed': 'bg-success'
    }
    return badges.get(status, 'bg-secondary')


def format_status_icon(status):
    """Return FontAwesome icon class for status."""
    icons = {
        'Pending': 'fa-clock',
        'Under Review': 'fa-search',
        'Action Taken': 'fa-tasks',
        'Closed': 'fa-check-circle'
    }
    return icons.get(status, 'fa-question-circle')


def truncate_text(text, length=100):
    """Truncate text to specified length with ellipsis."""
    if not text:
        return ''
    if len(text) <= length:
        return text
    return text[:length].rsplit(' ', 1)[0] + '...'


# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def validate_tracking_id(tracking_id):
    """
    Validate tracking ID format.
    
    Args:
        tracking_id: Tracking ID string to validate
    
    Returns:
        bool: True if valid format
    """
    if not tracking_id:
        return False
    
    # Must start with MIB and be 11 characters total (MIB + 8 chars)
    if not tracking_id.startswith('MIB'):
        return False
    
    # Must be at least 11 characters (MIB + 8 chars), allow longer for fallback IDs
    if len(tracking_id) < 11:
        return False
    
    # Remaining characters must be alphanumeric (uppercase letters or digits)
    random_part = tracking_id[3:]
    return random_part.isalnum() and random_part == random_part.upper()
