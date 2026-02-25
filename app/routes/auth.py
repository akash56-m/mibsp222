"""
MIBSP Authentication Routes
Login, logout, and session management.
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from datetime import datetime

from app import db
from app.models import User
from app.utils import log_action

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    User login page.
    Only for officers and admins - citizens don't need accounts.
    """
    # Redirect if already logged in
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('officer.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password.', 'warning')
            return render_template('auth/login.html')
        
        # Find user
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Contact an administrator.', 'danger')
                log_action('LOGIN_FAILED_INACTIVE', 
                          details={'username': username}, user=user)
                return render_template('auth/login.html')
            
            # Set session
            session.permanent = True
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['department_id'] = user.department_id
            
            # Update last login
            user.update_last_login()
            
            # Log successful login
            log_action('LOGIN_SUCCESS', user=user)
            
            flash(f'Welcome back, {user.username}!', 'success')
            
            # Redirect based on role
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            if user.is_admin():
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('officer.dashboard'))
        
        else:
            # Log failed login
            log_action('LOGIN_FAILED', 
                      details={'username': username, 'reason': 'invalid_credentials'})
            flash('Invalid username or password.', 'danger')
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    """Logout and clear session."""
    if 'user_id' in session:
        # Log logout
        user = User.query.get(session['user_id'])
        if user:
            log_action('LOGOUT', user=user)
        
        # Clear session
        session.clear()
        flash('You have been logged out.', 'info')
    
    return redirect(url_for('public.index'))


@auth_bp.route('/profile')
def profile():
    """User profile page."""
    from app.utils import login_required
    
    @login_required
    def get_profile():
        user = User.query.get(session['user_id'])
        return render_template('auth/profile.html', user=user)
    
    return get_profile()
