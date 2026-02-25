"""
MIBSP Public Routes Tests
Tests for citizen-facing functionality.
"""
import pytest
from app import create_app, db
from app.models import Department, Service, Complaint


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def sample_data(app):
    """Create sample data for tests."""
    with app.app_context():
        dept = Department(name='Test Department', description='Test')
        db.session.add(dept)
        db.session.commit()
        
        service = Service(name='Test Service', department_id=dept.id)
        db.session.add(service)
        db.session.commit()
        
        return {'department': dept, 'service': service}


class TestHomepage:
    """Tests for homepage."""
    
    def test_homepage_loads(self, client):
        """Test homepage loads successfully."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'MIBSP' in response.data
    
    def test_homepage_shows_stats(self, client):
        """Test homepage shows statistics."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Total Complaints' in response.data


class TestComplaintSubmission:
    """Tests for complaint submission."""
    
    def test_submit_page_loads(self, client):
        """Test submit page loads."""
        response = client.get('/submit')
        assert response.status_code == 200
        assert b'Submit Complaint' in response.data
    
    def test_submit_complaint_success(self, client, sample_data):
        """Test successful complaint submission."""
        response = client.post('/submit', data={
            'department_id': sample_data['department'].id,
            'service_id': sample_data['service'].id,
            'description': 'This is a test complaint with sufficient length for validation.'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Complaint submitted successfully' in response.data
        
        # Verify complaint was created
        complaint = Complaint.query.first()
        assert complaint is not None
        assert complaint.tracking_id.startswith('MIB')
    
    def test_submit_complaint_validation(self, client, sample_data):
        """Test complaint submission validation."""
        # Too short description
        response = client.post('/submit', data={
            'department_id': sample_data['department'].id,
            'service_id': sample_data['service'].id,
            'description': 'Short'
        })
        
        assert b'Description must be at least 50 characters' in response.data


class TestComplaintTracking:
    """Tests for complaint tracking."""
    
    def test_track_page_loads(self, client):
        """Test track page loads."""
        response = client.get('/track')
        assert response.status_code == 200
        assert b'Track Your Complaint' in response.data
    
    def test_track_complaint_found(self, client, sample_data):
        """Test tracking a valid complaint."""
        # Create a complaint first
        complaint = Complaint(
            tracking_id='MIBTEST1234',
            service_id=sample_data['service'].id,
            department_id=sample_data['department'].id,
            description='Test complaint for tracking'
        )
        db.session.add(complaint)
        db.session.commit()
        
        response = client.post('/track', data={
            'tracking_id': 'MIBTEST1234'
        })
        
        assert response.status_code == 200
        assert b'MIBTEST1234' in response.data
    
    def test_track_complaint_not_found(self, client):
        """Test tracking non-existent complaint."""
        response = client.post('/track', data={
            'tracking_id': 'MIBINVALID1'
        })
        
        assert b'Complaint not found' in response.data


class TestPublicDashboard:
    """Tests for public dashboard."""
    
    def test_dashboard_loads(self, client):
        """Test dashboard loads successfully."""
        response = client.get('/dashboard')
        assert response.status_code == 200
        assert b'Public Transparency Dashboard' in response.data


class TestAPIEndpoints:
    """Tests for public API endpoints."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        assert b'healthy' in response.data
    
    def test_get_stats(self, client):
        """Test stats API endpoint."""
        response = client.get('/api/stats')
        assert response.status_code == 200
        data = response.get_json()
        assert 'total' in data
        assert 'pending' in data
    
    def test_get_services(self, client, sample_data):
        """Test services API endpoint."""
        dept_id = sample_data['department'].id
        response = client.get(f'/api/services/{dept_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
