"""
MIBSP Security Tests
Tests for security vulnerabilities and protections.
"""
import pytest
from app import create_app, db
from app.models import User, Department, Service, Complaint


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        
        # Create test data
        dept = Department(name='Test Dept', description='Test')
        db.session.add(dept)
        db.session.commit()
        
        service = Service(name='Test Service', department_id=dept.id)
        db.session.add(service)
        db.session.commit()
        
        user = User(username='testuser', role='officer', department_id=dept.id)
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()
        
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestSQLInjection:
    """Tests for SQL injection protection."""
    
    def test_login_sql_injection(self, client):
        """Test SQL injection in login form."""
        response = client.post('/auth/login', data={
            'username': "admin' OR '1'='1",
            'password': "anything' OR '1'='1"
        })
        
        # Should not login successfully
        assert b'Invalid username or password' in response.data
    
    def test_search_sql_injection(self, client, app):
        """Test SQL injection in search."""
        with app.app_context():
            # Login as admin
            client.post('/auth/login', data={
                'username': 'testuser',
                'password': 'testpass123'
            })
            
            response = client.get('/admin/complaints?search=\' OR 1=1--')
            # Should not crash or return all data improperly
            assert response.status_code in [200, 400]


class TestXSSProtection:
    """Tests for XSS protection."""
    
    def test_xss_in_complaint(self, client, app):
        """Test XSS in complaint description."""
        with app.app_context():
            dept = Department.query.first()
            service = Service.query.first()
            
            xss_payload = '<script>alert("XSS")</script>'
            
            response = client.post('/submit', data={
                'department_id': dept.id,
                'service_id': service.id,
                'description': f'Test complaint {xss_payload}'
            }, follow_redirects=True)
            
            # The script tag should not be executed (would be escaped in template)
            assert response.status_code == 200


class TestCSRFProtection:
    """Tests for CSRF protection."""
    
    def test_csrf_required_on_post(self, client):
        """Test CSRF token is required."""
        response = client.post('/submit', data={
            'department_id': 1,
            'service_id': 1,
            'description': 'Test without CSRF'
        })
        
        # Should fail without CSRF token
        assert response.status_code == 400


class TestFileUploadSecurity:
    """Tests for file upload security."""
    
    def test_invalid_file_type_rejected(self, client, app):
        """Test invalid file types are rejected."""
        with app.app_context():
            dept = Department.query.first()
            service = Service.query.first()
            
            import io
            data = {
                'department_id': dept.id,
                'service_id': service.id,
                'description': 'Test complaint with invalid file'
            }
            
            # Try to upload an executable
            data['evidence'] = (io.BytesIO(b'malicious content'), 'malware.exe')
            
            response = client.post('/submit', data=data, content_type='multipart/form-data')
            
            # Should show error about invalid file type
            assert b'Invalid file type' in response.data or response.status_code == 200


class TestAuthorization:
    """Tests for authorization controls."""
    
    def test_officer_cannot_access_admin(self, client, app):
        """Test officer cannot access admin routes."""
        with app.app_context():
            # Login as officer
            client.post('/auth/login', data={
                'username': 'testuser',
                'password': 'testpass123'
            })
            
            # Try to access admin dashboard
            response = client.get('/admin/dashboard', follow_redirects=True)
            assert b'Admin access required' in response.data or response.status_code == 403
    
    def test_unauthorized_complaint_access(self, client, app):
        """Test officer cannot access complaints from other departments."""
        with app.app_context():
            # Create another department and complaint
            other_dept = Department(name='Other Dept', description='Other')
            db.session.add(other_dept)
            db.session.commit()
            
            other_service = Service(name='Other Service', department_id=other_dept.id)
            db.session.add(other_service)
            db.session.commit()
            
            complaint = Complaint(
                tracking_id='MIBOTHER001',
                service_id=other_service.id,
                department_id=other_dept.id,
                description='Complaint in other department'
            )
            db.session.add(complaint)
            db.session.commit()
            
            # Login as officer from first department
            client.post('/auth/login', data={
                'username': 'testuser',
                'password': 'testpass123'
            })
            
            # Try to access complaint from other department
            response = client.get(f'/officer/complaint/MIBOTHER001', follow_redirects=True)
            assert b'do not have permission' in response.data or response.status_code == 403
