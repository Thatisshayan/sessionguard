"""
File upload endpoint tests.
Tests file validation, size limits, virus scanning, and processing.
"""
import pytest
import io
from fastapi.testclient import TestClient
from pathlib import Path


class TestUploadEndpoints:
    """Test file upload endpoints."""
    
    def test_upload_csv_success(self, client: TestClient, sample_csv_file: Path):
        """Test successful CSV file upload."""
        with open(sample_csv_file, "rb") as f:
            response = client.post(
                "/api/v1/upload",
                files={"file": ("test_spins.csv", f, "text/csv")},
                data={"session_id": "1"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "upload_id" in data
        assert data["file_type"] == "csv"
        assert data["status"] in ["processing", "complete"]
        assert "virus_scan" in data
    
    def test_upload_png_success(self, client: TestClient):
        """Test successful image file upload."""
        image_content = b"fake image content for testing"
        response = client.post(
            "/api/v1/upload",
            files={"file": ("test.png", io.BytesIO(image_content), "image/png")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["file_type"] == "image"
        assert data["status"] == "complete"
    
    def test_upload_invalid_type(self, client: TestClient):
        """Test upload of unsupported file type."""
        response = client.post(
            "/api/v1/upload",
            files={"file": ("test.exe", io.BytesIO(b"executable content"), "application/x-msdownload")}
        )
        
        assert response.status_code == 415
    
    def test_upload_size_limit_enforced(self, client: TestClient):
        """Test that file size limit is enforced."""
        import backend.routes.uploads as uploads_module
        original = uploads_module.MAX_UPLOAD_SIZE_BYTES
        uploads_module.MAX_UPLOAD_SIZE_BYTES = 1
        
        try:
            content = b"x" * 1024
            response = client.post(
                "/api/v1/upload",
                files={"file": ("large.csv", io.BytesIO(content), "text/csv")}
            )
            
            assert response.status_code == 413
        finally:
            uploads_module.MAX_UPLOAD_SIZE_BYTES = original
    
    def test_upload_returns_file_size(self, client: TestClient):
        """Test that upload response includes file size."""
        test_content = b"test file content"
        response = client.post(
            "/api/v1/upload",
            files={"file": ("test.csv", io.BytesIO(test_content), "text/csv")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "file_size_bytes" in data
        assert data["file_size_bytes"] == len(test_content)
    
    def test_upload_list(self, client: TestClient):
        """Test listing uploads."""
        response = client.get("/api/v1/upload")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_upload_status(self, client: TestClient, sample_csv_file: Path):
        """Test getting upload status."""
        with open(sample_csv_file, "rb") as f:
            upload_response = client.post(
                "/api/v1/upload",
                files={"file": ("test_spins.csv", f, "text/csv")}
            )
        
        upload_id = upload_response.json()["upload_id"]
        
        response = client.get(f"/api/v1/upload/{upload_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == upload_id
        assert "status" in data
    
    def test_upload_status_not_found(self, client: TestClient):
        """Test getting status of nonexistent upload."""
        response = client.get("/api/v1/upload/99999/status")
        
        assert response.status_code == 404
    
    def test_download_csv_template_spin(self, client: TestClient):
        """Test downloading spin CSV template."""
        response = client.get("/api/v1/upload/template/spin")
        
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        content = response.text
        assert "timestamp" in content or "bet_amount" in content
    
    def test_download_csv_template_session(self, client: TestClient):
        """Test downloading session CSV template."""
        response = client.get("/api/v1/upload/template/session")
        
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        content = response.text
        assert "session" in content.lower() or "game" in content.lower()
    
    def test_download_csv_template_invalid(self, client: TestClient):
        """Test downloading invalid template type."""
        response = client.get("/api/v1/upload/template/invalid_type")
        
        assert response.status_code == 400
    
    def test_upload_rate_limiting(self, client: TestClient):
        """Test that upload endpoint is rate-limited."""
        for i in range(11):
            response = client.post(
                "/api/v1/upload",
                files={"file": (f"test{i}.csv", io.BytesIO(b"a,b\n1,2\n"), "text/csv")}
            )
            
            if i < 10:
                assert response.status_code == 200
            else:
                assert response.status_code == 429
    
    def test_virus_scan_graceful_degradation(self, client: TestClient):
        """Test that upload proceeds even when ClamAV is unavailable."""
        test_content = b"test file for virus scan"
        response = client.post(
            "/api/v1/upload",
            files={"file": ("test.csv", io.BytesIO(test_content), "text/csv")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "virus_scan" in data
    
    def test_upload_video_file(self, client: TestClient):
        """Test uploading a video file (simulated)."""
        video_content = b"fake video content for testing"
        response = client.post(
            "/api/v1/upload",
            files={"file": ("test.mp4", io.BytesIO(video_content), "video/mp4")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["file_type"] == "video"
        assert data["status"] == "processing"
