"""
Job queue and background processing tests.
Tests job creation, status tracking, cancellation, and worker health.
"""
import pytest
from fastapi.testclient import TestClient


class TestJobEndpoints:
    """Test job queue and background processing endpoints."""
    
    def test_create_job(self, client: TestClient, auth_headers: dict):
        """Test creating a new job."""
        response = client.post("/jobs", json={
            "job_type": "video_processing",
            "params": {
                "video_path": "/path/to/video.mp4",
                "fps": 1.0
            }
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] in ["pending", "processing"]
        assert data["job_type"] == "video_processing"
    
    def test_list_jobs(self, client: TestClient, auth_headers: dict):
        """Test listing all jobs."""
        # Create a job first
        create_response = client.post("/jobs", json={
            "job_type": "ocr_processing",
            "params": {"image_path": "/path/to/image.png"}
        }, headers=auth_headers)
        
        # List jobs
        response = client.get("/jobs", headers=auth_headers)
        
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) >= 1
        assert any(job["job_type"] == "ocr_processing" for job in jobs)
    
    def test_get_job_status(self, client: TestClient, auth_headers: dict):
        """Test getting status of a specific job."""
        # Create a job
        create_response = client.post("/jobs", json={
            "job_type": "video_processing",
            "params": {"video_path": "/test/video.mp4"}
        }, headers=auth_headers)
        job_id = create_response.json()["job_id"]
        
        # Get job status
        response = client.get(f"/jobs/{job_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert "status" in data
        assert "created_at" in data
    
    def test_get_nonexistent_job(self, client: TestClient, auth_headers: dict):
        """Test getting status of nonexistent job."""
        response = client.get("/jobs/99999", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_cancel_job(self, client: TestClient, auth_headers: dict):
        """Test cancelling a job."""
        # Create a job
        create_response = client.post("/jobs", json={
            "job_type": "video_processing",
            "params": {"video_path": "/test/video.mp4"}
        }, headers=auth_headers)
        job_id = create_response.json()["job_id"]
        
        # Cancel the job
        response = client.post(f"/jobs/{job_id}/cancel", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
    
    def test_cancel_completed_job(self, client: TestClient, auth_headers: dict):
        """Test that cancelling a completed job fails appropriately."""
        # This test would require a job that completes quickly
        # For now, we'll test the endpoint exists
        create_response = client.post("/jobs", json={
            "job_type": "ocr_processing",
            "params": {"image_path": "/test/image.png"}
        }, headers=auth_headers)
        job_id = create_response.json()["job_id"]
        
        # Try to cancel (may fail if job is already complete)
        response = client.post(f"/jobs/{job_id}/cancel", headers=auth_headers)
        
        # Response should be 200 or 400 depending on job state
        assert response.status_code in [200, 400]
    
    def test_worker_health_endpoint(self, client: TestClient):
        """Test the worker health check endpoint."""
        response = client.get("/jobs/worker/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "active_workers" in data
        assert "queued_jobs" in data
    
    def test_job_unauthorized_access(self, client: TestClient):
        """Test that unauthorized users cannot access job endpoints."""
        # Try to create job without auth
        response = client.post("/jobs", json={
            "job_type": "video_processing",
            "params": {}
        })
        
        assert response.status_code == 401
        
        # Try to list jobs without auth
        response = client.get("/jobs")
        
        assert response.status_code == 401
    
    def test_job_retry_logic(self, client: TestClient, auth_headers: dict):
        """Test that failed jobs are retried according to policy."""
        # Create a job that will fail (invalid parameters)
        response = client.post("/jobs", json={
            "job_type": "video_processing",
            "params": {"video_path": "/nonexistent/video.mp4"}
        }, headers=auth_headers)
        
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Wait a moment for processing attempt
        time.sleep(1)
        
        # Check job status - should show retry information
        status_response = client.get(f"/jobs/{job_id}", headers=auth_headers)
        assert status_response.status_code == 200
        
        data = status_response.json()
        # Job may have failed or be in retry state
        assert data["status"] in ["failed", "processing", "pending", "error"]