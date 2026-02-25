"""
MIBSP Public Routes
Citizen-facing routes - no authentication required.
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta

from app import db
from app.models import Department, Service, Complaint, AuditLog
from app.utils import (
    generate_tracking_id, save_uploaded_file, 
    validate_tracking_id, log_action
)

public_bp = Blueprint('public', __name__)


# =============================================================================
# HOMEPAGE & STATIC PAGES
# =============================================================================

@public_bp.route('/')
def index():
    """Homepage with hero section and quick stats."""
    stats = Complaint.get_stats()
    departments = Department.query.all()
    
    return render_template('public/index.html', 
                          stats=stats, 
                          departments=departments)


@public_bp.route('/about')
def about():
    """About page explaining the portal."""
    return render_template('public/about.html')


@public_bp.route('/how-it-works')
def how_it_works():
    """How it works page with process explanation."""
    return render_template('public/how_it_works.html')


# =============================================================================
# COMPLAINT SUBMISSION
# =============================================================================

@public_bp.route('/submit', methods=['GET', 'POST'])
def submit_complaint():
    """
    Anonymous complaint submission form.
    No login required, no PII collected.
    """
    if request.method == 'POST':
        # Get form data
        department_id = request.form.get('department_id', type=int)
        service_id = request.form.get('service_id', type=int)
        description = request.form.get('description', '').strip()
        
        # Server-side validation
        errors = []
        
        if not department_id:
            errors.append('Please select a department.')
        if not service_id:
            errors.append('Please select a service.')
        if not description or len(description) < 50:
            errors.append('Description must be at least 50 characters.')
        if len(description) > 5000:
            errors.append('Description must not exceed 5000 characters.')
        
        # Validate department and service relationship
        if department_id and service_id:
            service = Service.query.get(service_id)
            if not service or service.department_id != department_id:
                errors.append('Invalid service selection for this department.')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            departments = Department.query.all()
            return render_template('public/submit.html', 
                                  departments=departments,
                                  form_data=request.form)
        
        # Handle file upload
        evidence_path = None
        if 'evidence' in request.files:
            file = request.files['evidence']
            if file and file.filename:
                success, result = save_uploaded_file(file)
                if success:
                    evidence_path = result
                else:
                    flash(f'File upload error: {result}', 'warning')
        
        # Create complaint
        try:
            complaint = Complaint(
                tracking_id=generate_tracking_id(),
                service_id=service_id,
                department_id=department_id,
                description=description,
                evidence_path=evidence_path,
                status='Pending'
            )
            
            db.session.add(complaint)
            db.session.commit()
            
            # Log the submission (anonymous - no user)
            log_action('COMPLAINT_SUBMITTED', 
                      details={'tracking_id': complaint.tracking_id})
            
            flash('Complaint submitted successfully!', 'success')
            return redirect(url_for('public.confirmation', 
                                   tracking_id=complaint.tracking_id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Complaint submission error: {str(e)}')
            flash('Error submitting complaint. Please try again.', 'danger')
            departments = Department.query.all()
            return render_template('public/submit.html', 
                                  departments=departments,
                                  form_data=request.form)
    
    # GET request - show form
    departments = Department.query.all()
    return render_template('public/submit.html', departments=departments)


@public_bp.route('/confirmation/<tracking_id>')
def confirmation(tracking_id):
    """Confirmation page showing tracking ID."""
    complaint = Complaint.query.filter_by(tracking_id=tracking_id).first_or_404()
    return render_template('public/confirm.html', complaint=complaint)


# =============================================================================
# COMPLAINT TRACKING
# =============================================================================

@public_bp.route('/track', methods=['GET', 'POST'])
def track_complaint():
    """
    Public complaint tracking - no login required.
    Only shows non-sensitive information.
    """
    complaint = None
    tracking_id = None
    
    if request.method == 'POST':
        tracking_id = request.form.get('tracking_id', '').strip().upper()
        
        if not tracking_id:
            flash('Please enter a tracking ID.', 'warning')
        elif not validate_tracking_id(tracking_id):
            flash('Invalid tracking ID format.', 'danger')
        else:
            complaint = Complaint.query.filter_by(tracking_id=tracking_id).first()
            
            if not complaint:
                flash('Complaint not found. Please check your tracking ID.', 'warning')
            else:
                # Log tracking access (anonymous)
                log_action('COMPLAINT_TRACKED', 
                          details={'tracking_id': tracking_id})
    
    return render_template('public/track.html', 
                          complaint=complaint, 
                          tracking_id=tracking_id)


# =============================================================================
# PUBLIC DASHBOARD
# =============================================================================

@public_bp.route('/dashboard')
def public_dashboard():
    """
    Public analytics dashboard.
    Shows aggregate statistics only - no sensitive data.
    """
    # Overall stats
    stats = Complaint.get_stats()
    
    # Department breakdown
    departments = Department.query.all()
    dept_stats = []
    for dept in departments:
        dept_complaints = Complaint.query.filter_by(department_id=dept.id)
        dept_stats.append({
            'name': dept.name,
            'total': dept_complaints.count(),
            'pending': dept_complaints.filter_by(status='Pending').count(),
            'closed': dept_complaints.filter_by(status='Closed').count()
        })
    
    # Recent activity (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_complaints = Complaint.query.filter(
        Complaint.submitted_at >= thirty_days_ago
    ).order_by(Complaint.submitted_at.desc()).limit(10).all()
    
    return render_template('public/dashboard.html',
                          stats=stats,
                          dept_stats=dept_stats,
                          recent_complaints=recent_complaints)


# =============================================================================
# API ENDPOINTS
# =============================================================================

@public_bp.route('/api/services/<int:department_id>')
def get_services(department_id):
    """
    AJAX endpoint to get services for a department.
    Used in complaint form for dynamic service dropdown.
    """
    services = Service.query.filter_by(department_id=department_id).all()
    return jsonify([service.to_dict() for service in services])


@public_bp.route('/api/stats')
def get_stats():
    """API endpoint for statistics (used by charts)."""
    return jsonify(Complaint.get_stats())


@public_bp.route('/api/chart/monthly')
def get_monthly_chart_data():
    """Get monthly complaint data for Chart.js."""
    from sqlalchemy import extract, func
    
    # Last 12 months
    months = []
    counts = []
    
    for i in range(11, -1, -1):
        date = datetime.utcnow() - timedelta(days=i*30)
        month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get count for this month
        count = Complaint.query.filter(
            extract('year', Complaint.submitted_at) == month_start.year,
            extract('month', Complaint.submitted_at) == month_start.month
        ).count()
        
        months.append(month_start.strftime('%b %Y'))
        counts.append(count)
    
    return jsonify({
        'labels': months,
        'data': counts
    })


@public_bp.route('/api/chart/dept')
def get_dept_chart_data():
    """Get department-wise complaint data for Chart.js."""
    departments = Department.query.all()
    
    labels = []
    data = []
    
    for dept in departments:
        count = Complaint.query.filter_by(department_id=dept.id).count()
        labels.append(dept.name)
        data.append(count)
    
    return jsonify({
        'labels': labels,
        'data': data
    })


@public_bp.route('/api/chart/status')
def get_status_chart_data():
    """Get status breakdown for Chart.js doughnut chart."""
    statuses = ['Pending', 'Under Review', 'Action Taken', 'Closed']
    data = []
    
    for status in statuses:
        count = Complaint.query.filter_by(status=status).count()
        data.append(count)
    
    return jsonify({
        'labels': statuses,
        'data': data
    })


# =============================================================================
# HEALTH CHECK
# =============================================================================

@public_bp.route('/health')
def health_check():
    """Health check endpoint for monitoring."""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503
