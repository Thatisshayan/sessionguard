"""
Job queue and background processing tests.
Tests job creation, status tracking, cancellation, and worker health.
"""
import time
import pytest
from fastapi.testclient import TestClient


class TestJobEndpoints:
    """Test job queue and background processing endpoints."""
    
    def test_create_job(self, client: TestClient, auth_headers: dict):
        """Test creating a new job."""
        response = client.post("/api/v1/jobs", json={
            "job_type": "video_pipeline",
            "session_id": 1
        }, headers=auth_headers)
        
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] in ["pending", "processing"]
        assert data["job_type"] == "video_pipeline"
    
    def test_list_jobs(self, client: TestClient, auth_headers: dict):
        """Test listing all jobs."""
        client.post("/api/v1/jobs", json={
            "job_type": "csv_parse",
            "session_id": 1
        }, headers=auth_headers)
        
        response = client.get("/api/v1/jobs", headers=auth_headers)
        
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) >= 1
    
    def test_get_job_status(self, client: TestClient, auth_headers: dict):
        """Test getting status of a specific job."""
        create_response = client.post("/api/v1/jobs", json={
            "job_type": "video_pipeline",
            "session_id": 1
        }, headers=auth_headers)
        job_id = create_response.json()["job_id"]
        
        response = client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    def test_get_nonexistent_job(self, client: TestClient, auth_headers: dict):
        """Test getting status of nonexistent job."""
        response = client.get("/api/v1/jobs/99999", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_cancel_job(self, client: TestClient, auth_headers: dict):
        """Test cancelling a job."""
        create_response = client.post("/api/v1/jobs", json={
            "job_type": "video_pipeline",
            "session_id": 1
        }, headers=auth_headers)
        job_id = create_response.json()["job_id"]
        
        response = client.post(f"/api/v1/jobs/{job_id}/cancel", headers=auth_headers)
        
        assert response.status_code in [200, 409]
    
    def test_worker_health_endpoint(self, client: TestClient):
        """Test the worker health check endpoint."""
        response = client.get("/api/v1/jobs/worker/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "active_jobs" in data
        assert "max_workers" in data
        assert "pending_jobs" in data
    
    def test_job_list_requires_auth(self, client: TestClient):
        """Test that listing jobs without auth still works (optional auth)."""
        response = client.get("/api/v1/jobs")
        
        assert response.status_code == 200
    
    def test_invalid_job_type(self, client: TestClient, auth_headers: dict):
        """Test that invalid job types are rejected."""
        response = client.post("/api/v1/jobs", json={
            "job_type": "nonexistent_type",
            "session_id": 1
        }, headers=auth_headers)
        
        assert response.status_code == 400
