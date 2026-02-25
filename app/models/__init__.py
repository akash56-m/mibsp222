"""
MIBSP Database Models
All SQLAlchemy models for the Municipal Integrity & Bribe-Free Service Portal.
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib
import json

from app import db


class Department(db.Model):
    """
    Government department/ward entity.
    Examples: Water Supply, Roads & Infrastructure, Public Health, etc.
    """
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    services = db.relationship('Service', backref='department', lazy='dynamic',
                               cascade='all, delete-orphan')
    users = db.relationship('User', backref='department', lazy='dynamic')
    complaints = db.relationship('Complaint', backref='department', lazy='dynamic')
    
    def __repr__(self):
        return f'<Department {self.name}>'
    
    def to_dict(self):
        """Serialize department to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'service_count': self.services.count(),
            'complaint_count': self.complaints.count()
        }


class Service(db.Model):
    """
    Service offered by a department.
    Citizens select department first, then service via AJAX.
    """
    __tablename__ = 'services'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    complaints = db.relationship('Complaint', backref='service', lazy='dynamic')
    
    def __repr__(self):
        return f'<Service {self.name} ({self.department.name if self.department else "No Dept"})>'
    
    def to_dict(self):
        """Serialize service to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'department_id': self.department_id,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class User(db.Model):
    """
    System user - Admin or Officer.
    Citizens do NOT have accounts (anonymous submission).
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False, unique=True, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='officer')  # 'admin' or 'officer'
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    assigned_complaints = db.relationship('Complaint', backref='assigned_officer',
                                          foreign_keys='Complaint.assigned_to', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
    
    def set_password(self, password):
        """Hash and set password using PBKDF2-SHA256."""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
    
    def check_password(self, password):
        """Verify password against hash."""
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Check if user has admin role."""
        return self.role == 'admin'
    
    def is_officer(self):
        """Check if user has officer role."""
        return self.role == 'officer'
    
    def can_access_complaint(self, complaint):
        """Check if user can access/modify a specific complaint."""
        if self.is_admin():
            return True
        if self.is_officer() and complaint.department_id == self.department_id:
            if complaint.assigned_to is None or complaint.assigned_to == self.id:
                return True
        return False
    
    def update_last_login(self):
        """Update last login timestamp."""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self):
        """Serialize user to dictionary (safe - no password)."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'department_id': self.department_id,
            'department_name': self.department.name if self.department else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class Complaint(db.Model):
    """
    Citizen complaint - completely anonymous.
    No PII stored (no name, phone, email, IP address).
    """
    __tablename__ = 'complaints'
    
    id = db.Column(db.Integer, primary_key=True)
    tracking_id = db.Column(db.String(12), nullable=False, unique=True, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    evidence_path = db.Column(db.String(256), nullable=True)
    status = db.Column(db.String(30), default='Pending', nullable=False, index=True)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
    
    # Valid status transitions
    VALID_STATUSES = ['Pending', 'Under Review', 'Action Taken', 'Closed']
    STATUS_FLOW = {
        'Pending': ['Under Review', 'Closed'],
        'Under Review': ['Action Taken', 'Closed'],
        'Action Taken': ['Closed'],
        'Closed': []
    }
    
    def __repr__(self):
        return f'<Complaint {self.tracking_id} ({self.status})>'
    
    def can_transition_to(self, new_status):
        """Check if status transition is valid."""
        return new_status in self.STATUS_FLOW.get(self.status, [])
    
    def update_status(self, new_status, notes=None, user=None):
        """
        Update complaint status with validation.
        Returns tuple (success: bool, message: str)
        """
        if not self.can_transition_to(new_status):
            return False, f"Cannot transition from '{self.status}' to '{new_status}'"
        
        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.utcnow()
        
        if new_status == 'Closed':
            self.resolved_at = datetime.utcnow()
        
        if notes:
            self.resolution_notes = notes
        
        return True, f"Status updated from '{old_status}' to '{new_status}'"
    
    def get_resolution_time(self):
        """Calculate resolution time in hours."""
        if self.resolved_at and self.submitted_at:
            delta = self.resolved_at - self.submitted_at
            return round(delta.total_seconds() / 3600, 2)
        return None
    
    def to_dict(self, include_details=False):
        """Serialize complaint to dictionary."""
        data = {
            'id': self.id,
            'tracking_id': self.tracking_id,
            'service_id': self.service_id,
            'service_name': self.service.name if self.service else None,
            'department_id': self.department_id,
            'department_name': self.department.name if self.department else None,
            'status': self.status,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }
        
        if include_details:
            data.update({
                'description': self.description,
                'has_evidence': self.evidence_path is not None,
                'assigned_to': self.assigned_to,
                'officer_name': self.assigned_officer.username if self.assigned_officer else None,
                'resolution_notes': self.resolution_notes,
                'resolution_hours': self.get_resolution_time()
            })
        
        return data
    
    @staticmethod
    def get_stats():
        """Get aggregate statistics for dashboard."""
        total = Complaint.query.count()
        pending = Complaint.query.filter_by(status='Pending').count()
        under_review = Complaint.query.filter_by(status='Under Review').count()
        action_taken = Complaint.query.filter_by(status='Action Taken').count()
        closed = Complaint.query.filter_by(status='Closed').count()
        
        return {
            'total': total,
            'pending': pending,
            'under_review': under_review,
            'action_taken': action_taken,
            'closed': closed,
            'resolution_rate': round((closed / total * 100), 2) if total > 0 else 0
        }


class AuditLog(db.Model):
    """
    Immutable audit log with hash chaining for tamper evidence.
    Inspired by blockchain - each entry contains hash of previous entry.
    NO UPDATE OR DELETE routes exist for this table.
    """
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    username = db.Column(db.String(64), nullable=False, index=True)
    role = db.Column(db.String(30), nullable=False)
    action = db.Column(db.String(120), nullable=False, index=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 compatible
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    previous_hash = db.Column(db.String(64), nullable=True)
    row_hash = db.Column(db.String(64), nullable=False, unique=True)
    
    def __repr__(self):
        return f'<AuditLog {self.username} {self.action} at {self.timestamp}>'
    
    def calculate_hash(self):
        """
        Calculate SHA-256 hash of this log entry.
        Includes previous hash for chain integrity.
        """
        data = {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'action': self.action,
            'details': self.details or '',
            'timestamp': self.timestamp.isoformat() if self.timestamp else '',
            'previous_hash': self.previous_hash or ''
        }
        
        # Create deterministic string representation
        hash_string = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(hash_string.encode()).hexdigest()
    
    def verify_integrity(self):
        """Verify that stored hash matches calculated hash."""
        return self.row_hash == self.calculate_hash()
    
    @staticmethod
    def get_previous_hash():
        """Get hash of most recent audit log entry."""
        last_log = AuditLog.query.order_by(AuditLog.id.desc()).first()
        return last_log.row_hash if last_log else None
    
    @staticmethod
    def create_entry(username, role, action, details=None, user_id=None, ip_address=None):
        """
        Factory method to create a new audit log entry.
        Automatically handles hash chaining.
        """
        entry = AuditLog(
            user_id=user_id,
            username=username,
            role=role,
            action=action,
            details=details,
            ip_address=ip_address,
            previous_hash=AuditLog.get_previous_hash()
        )
        
        # Calculate hash after setting all fields
        entry.row_hash = entry.calculate_hash()
        
        db.session.add(entry)
        db.session.commit()
        
        return entry
    
    def to_dict(self):
        """Serialize audit log to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'action': self.action,
            'details': self.details,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'row_hash': self.row_hash[:16] + '...'  # Truncated for display
        }
