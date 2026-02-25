"""
MIBSP Authentication Tests
Tests for login, logout, and session management.
"""
import pytest
from app import create_app, db
from app.models import User


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        # Create test user
        user = User(username='testuser', role='officer')
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


class TestLogin:
    """Tests for login functionality."""
    
    def test_login_page_loads(self, client):
        """Test login page loads."""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'Staff Login' in response.data
    
    def test_login_success(self, client):
        """Test successful login."""
        response = client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Welcome back' in response.data
    
    def test_login_wrong_password(self, client):
        """Test login with wrong password."""
        response = client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        assert b'Invalid username or password' in response.data
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = client.post('/auth/login', data={
            'username': 'nonexistent',
            'password': 'somepassword'
        })
        
        assert b'Invalid username or password' in response.data


class TestLogout:
    """Tests for logout functionality."""
    
    def test_logout(self, client):
        """Test logout functionality."""
        # Login first
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Then logout
        response = client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200
        assert b'logged out' in response.data


class TestSessionProtection:
    """Tests for session security."""
    
    def test_protected_route_redirects(self, client):
        """Test protected route redirects when not logged in."""
        response = client.get('/officer/dashboard', follow_redirects=True)
        assert b'Please log in' in response.data
    
    def test_session_persists(self, client):
        """Test session persists across requests."""
        # Login
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Access protected page
        response = client.get('/officer/dashboard')
        assert response.status_code == 200
