#!/usr/bin/env python3
"""
MIBSP Database Seeder
Creates demo data for development and testing.
"""
import os
import sys
from datetime import datetime, timedelta
import random

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Department, Service, User, Complaint, AuditLog


def seed_departments():
    """Create default departments."""
    departments_data = [
        {
            'name': 'Water Supply',
            'description': 'Water supply, distribution, and related services'
        },
        {
            'name': 'Roads & Infrastructure',
            'description': 'Road maintenance, street lights, and public infrastructure'
        },
        {
            'name': 'Public Health',
            'description': 'Public health services, sanitation, and hygiene'
        },
        {
            'name': 'Electricity',
            'description': 'Electricity supply and power-related services'
        },
        {
            'name': 'Sanitation',
            'description': 'Waste management and sanitation services'
        }
    ]
    
    departments = []
    for data in departments_data:
        dept = Department.query.filter_by(name=data['name']).first()
        if not dept:
            dept = Department(**data)
            db.session.add(dept)
            print(f"  Created department: {data['name']}")
        departments.append(dept)
    
    db.session.commit()
    return departments


def seed_services(departments):
    """Create services for each department."""
    services_data = {
        'Water Supply': [
            'Water Connection',
            'Water Quality Issue',
            'Pipeline Leakage',
            'Billing Complaint'
        ],
        'Roads & Infrastructure': [
            'Pothole Repair',
            'Street Light Issue',
            'Road Construction',
            'Drainage Problem'
        ],
        'Public Health': [
            'Mosquito Menace',
            'Garbage Collection',
            'Public Toilet Maintenance',
            'Health Violation'
        ],
        'Electricity': [
            'Power Outage',
            'Voltage Issue',
            'New Connection',
            'Meter Complaint'
        ],
        'Sanitation': [
            'Sewage Blockage',
            'Waste Collection',
            'Drain Cleaning',
            'Public Cleanliness'
        ]
    }
    
    services = []
    for dept in departments:
        dept_services = services_data.get(dept.name, [])
        for service_name in dept_services:
            existing = Service.query.filter_by(name=service_name, department_id=dept.id).first()
            if not existing:
                service = Service(
                    name=service_name,
                    department_id=dept.id,
                    description=f'{service_name} services'
                )
                db.session.add(service)
                print(f"  Created service: {service_name} ({dept.name})")
                services.append(service)
    
    db.session.commit()
    return services


def seed_users(departments):
    """Create admin and officer users."""
    users_created = []
    
    # Create admin
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@mibsp.gov.in',
            role='admin',
            is_active=True
        )
        admin.set_password('Admin@1234')
        db.session.add(admin)
        users_created.append(('admin', 'Admin@1234', 'admin'))
        print("  Created user: admin (role: admin)")
    
    # Create officers
    officer_data = [
        ('officer_water', 'Water Supply'),
        ('officer_roads', 'Roads & Infrastructure'),
        ('officer_health', 'Public Health')
    ]
    
    for username, dept_name in officer_data:
        existing = User.query.filter_by(username=username).first()
        if not existing:
            dept = Department.query.filter_by(name=dept_name).first()
            officer = User(
                username=username,
                email=f'{username}@mibsp.gov.in',
                role='officer',
                department_id=dept.id if dept else None,
                is_active=True
            )
            officer.set_password('Officer@1234')
            db.session.add(officer)
            users_created.append((username, 'Officer@1234', 'officer'))
            print(f"  Created user: {username} (role: officer, dept: {dept_name})")
    
    db.session.commit()
    return users_created


def seed_complaints(departments, services):
    """Create sample complaints."""
    sample_descriptions = [
        "Water supply has been irregular for the past week. We are facing severe shortage.",
        "There is a large pothole on the main road causing accidents. Immediate repair needed.",
        "Garbage has not been collected for 3 days. Foul smell and health hazard.",
        "Street light not working for past 2 weeks. Area is dark and unsafe.",
        "Sewage overflow on the street. Request immediate cleaning.",
        "Power outage for 6 hours daily. Affecting work and daily life.",
        "Water quality is poor with bad smell and color. Not fit for consumption.",
        "Drainage blocked causing waterlogging during rains. Need urgent attention.",
        "Mosquito breeding in stagnant water. Risk of dengue outbreak.",
        "Illegal construction blocking road access. Please take action.",
        "Public toilet not maintained properly. Unhygienic conditions.",
        "Voltage fluctuations damaging electrical appliances. Need stabilizer.",
        "New water connection requested 2 months ago. No response yet.",
        "Road construction incomplete for past 3 months. Commuters suffering.",
        "Waste segregation not being followed. Need awareness and enforcement."
    ]
    
    statuses = ['Pending', 'Under Review', 'Action Taken', 'Closed']
    status_weights = [0.3, 0.3, 0.2, 0.2]
    
    officers = User.query.filter_by(role='officer').all()
    complaints_created = []
    
    # Create 20 sample complaints
    for i in range(20):
        dept = random.choice(departments)
        dept_services = [s for s in services if s.department_id == dept.id]
        service = random.choice(dept_services) if dept_services else None
        
        # Generate random dates within last 3 months
        days_ago = random.randint(1, 90)
        submitted_at = datetime.utcnow() - timedelta(days=days_ago)
        
        # Determine status
        status = random.choices(statuses, weights=status_weights)[0]
        
        # Create complaint
        complaint = Complaint(
            tracking_id=f'MIB{random.randint(10000000, 99999999)}',
            service_id=service.id if service else None,
            department_id=dept.id,
            description=random.choice(sample_descriptions),
            status=status,
            submitted_at=submitted_at,
            updated_at=submitted_at
        )
        
        # Assign to officer if not pending
        if status != 'Pending' and officers:
            dept_officers = [o for o in officers if o.department_id == dept.id]
            if dept_officers:
                complaint.assigned_to = random.choice(dept_officers).id
        
        # Add resolution data if closed
        if status == 'Closed':
            complaint.resolved_at = submitted_at + timedelta(days=random.randint(3, 30))
            complaint.updated_at = complaint.resolved_at
            complaint.resolution_notes = "Complaint resolved. Appropriate action taken."
        
        db.session.add(complaint)
        complaints_created.append(complaint)
        print(f"  Created complaint: {complaint.tracking_id} ({status})")
    
    db.session.commit()
    return complaints_created


def seed_audit_logs(users):
    """Create sample audit logs."""
    actions = [
        'LOGIN_SUCCESS',
        'COMPLAINT_SUBMITTED',
        'STATUS_UPDATE',
        'NOTES_ADDED',
        'COMPLAINT_ASSIGNED'
    ]
    
    for _ in range(30):
        user = random.choice(users) if users else None
        action = random.choice(actions)
        
        log = AuditLog.create_entry(
            user_id=user.id if user else None,
            username=user.username if user else 'anonymous',
            role=user.role if user else 'guest',
            action=action,
            details=f'Sample {action.lower()} entry',
            ip_address=f'192.168.1.{random.randint(1, 255)}'
        )
        print(f"  Created audit log: {action} by {log.username}")


def print_summary(users, complaints):
    """Print seeding summary."""
    print("\n" + "="*60)
    print("  SEEDING COMPLETE")
    print("="*60)
    print("\nCreated Users:")
    print("-" * 40)
    for username, password, role in users:
        print(f"  Username: {username}")
        print(f"  Password: {password}")
        print(f"  Role: {role}")
        print()
    
    print("\nSample Complaint Tracking IDs:")
    print("-" * 40)
    for complaint in complaints[:5]:
        print(f"  {complaint.tracking_id} - {complaint.status}")
    
    print("\n" + "="*60)
    print("  IMPORTANT: Change default passwords immediately!")
    print("="*60)


def main():
    """Main seeding function."""
    print("\n" + "="*60)
    print("  MIBSP Database Seeder")
    print("="*60 + "\n")
    
    # Create app context
    env = os.environ.get('FLASK_ENV', 'development')
    app = create_app(env)
    
    with app.app_context():
        print("Creating departments...")
        departments = seed_departments()
        
        print("\nCreating services...")
        services = seed_services(departments)
        
        print("\nCreating users...")
        users = seed_users(departments)
        
        print("\nCreating complaints...")
        complaints = seed_complaints(departments, services)
        
        print("\nCreating audit logs...")
        all_users = User.query.all()
        seed_audit_logs(all_users)
        
        print_summary(users, complaints)


if __name__ == '__main__':
    main()
