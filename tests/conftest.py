"""
Test configuration and shared fixtures for SessionGuard test suite.
"""
import os
import tempfile
import shutil
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient

# Add parent directory to path for imports
import sys
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.main import app
from database.db import get_connection, get_db_path, init_db, init_db_v2, init_db_v3, init_db_v4, init_db_v5, init_db_v6, init_db_v7


@pytest.fixture(scope="function")
def test_db() -> Generator:
    """
    Create a temporary test database for each test.
    Ensures tests don't interfere with each other or the development database.
    """
    # Create temporary directory for test database
    temp_dir = tempfile.mkdtemp()
    test_db_path = Path(temp_dir) / "test_sessionguard.db"
    
    # Monkey-patch get_db_path to return test database
    import database.db as db_module
    original_get_db_path = db_module.get_db_path
    
    def mock_get_db_path() -> str:
        return str(test_db_path)
    
    db_module.get_db_path = mock_get_db_path
    
    # Initialize test database
    init_db()
    init_db_v2()
    init_db_v3()
    init_db_v4()
    init_db_v5()
    init_db_v6()
    init_db_v7()
    
    yield test_db_path
    
    # Restore original function
    db_module.get_db_path = original_get_db_path
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def client(test_db: Path) -> Generator:
    """
    Create a test client for the FastAPI app.
    Uses the test database fixture.
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def auth_headers(client: TestClient) -> dict:
    """
    Create a test user and return authentication headers.
    """
    # Signup a test user
    signup_response = client.post("/api/v1/auth/signup", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword123"
    })
    
    # Login to get tokens
    login_response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "testpassword123"
    })
    
    assert login_response.status_code == 200
    tokens = login_response.json()
    
    return {
        "Authorization": f"Bearer {tokens['access_token']}",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="function")
def admin_headers(client: TestClient) -> dict:
    """
    Create an admin user and return authentication headers.
    """
    # Create admin user directly in DB (bypassing signup for admin role)
    import hashlib
    from database.db import get_connection
    
    conn = get_connection()
    salt = os.urandom(16).hex()
    password_hash = hashlib.pbkdf2_hmac('sha256', b'adminpassword123', salt.encode(), 260000).hex()
    
    conn.execute(
        "INSERT INTO users (email, hashed_password, salt, role) VALUES (?, ?, ?, ?)",
        ("admin@example.com", password_hash, salt, "admin")
    )
    conn.commit()
    conn.close()
    
    # Login as admin
    login_response = client.post("/api/v1/auth/login", json={
        "email": "admin@example.com",
        "password": "adminpassword123"
    })
    
    assert login_response.status_code == 200
    tokens = login_response.json()
    
    return {
        "Authorization": f"Bearer {tokens['access_token']}",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="function")
def sample_session_data(client: TestClient, auth_headers: dict) -> dict:
    """
    Create a sample session for testing.
    """
    session_data = {
        "game_name": "Test Slot Game",
        "start_time": "2024-01-01T10:00:00",
        "end_time": "2024-01-01T11:00:00",
        "initial_balance": 1000.00,
        "final_balance": 950.00,
        "total_spins": 100,
        "total_wagered": 500.00,
        "total_won": 450.00
    }
    
    response = client.post("/api/v1/sessions", json=session_data, headers=auth_headers)
    assert response.status_code == 200
    
    return response.json()


@pytest.fixture(scope="function")
def sample_csv_file() -> Path:
    """
    Create a sample CSV file for upload testing.
    """
    temp_dir = tempfile.mkdtemp()
    csv_path = Path(temp_dir) / "test_spins.csv"
    
    csv_content = """timestamp,bet_amount,win_amount,balance
2024-01-01T10:00:00,5.00,0.00,995.00
2024-01-01T10:00:30,5.00,10.00,1000.00
2024-01-01T10:01:00,5.00,0.00,995.00
2024-01-01T10:01:30,5.00,25.00,1015.00
"""
    
    csv_path.write_text(csv_content)
    yield csv_path
    
    shutil.rmtree(temp_dir, ignore_errors=True)