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
                "/upload",
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
        # Create a simple image-like file
        image_content = b"fake image content for testing"
        response = client.post(
            "/upload",
            files={"file": ("test.png", io.BytesIO(image_content), "image/png")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["file_type"] == "image"
        assert data["status"] == "complete"  # Images don't need processing
    
    def test_upload_invalid_type(self, client: TestClient):
        """Test upload of unsupported file type."""
        response = client.post(
            "/upload",
            files={"file": ("test.exe", io.BytesIO(b"executable content"), "application/x-msdownload")}
        )
        
        assert response.status_code == 415  # Unsupported Media Type
    
    def test_upload_size_limit_enforced(self, client: TestClient):
        """Test that file size limit is enforced."""
        # Create a file larger than default 2GB limit (simulated with small file for test)
        # In actual test, you'd need to adjust UPLOAD_MAX_SIZE_MB env var
        import os
        original_limit = os.environ.get("UPLOAD_MAX_SIZE_MB")
        os.environ["UPLOAD_MAX_SIZE_MB"] = "1"  # Set to 1MB for testing
        
        try:
            # Create a 2MB file (exceeds 1MB limit)
            large_content = b"x" * (2 * 1024 * 1024)
            response = client.post(
                "/upload",
                files={"file": ("large.txt", io.BytesIO(large_content), "text/plain")}
            )
            
            assert response.status_code == 413  # Payload Too Large
        finally:
            if original_limit:
                os.environ["UPLOAD_MAX_SIZE_MB"] = original_limit
            else:
                os.environ.pop("UPLOAD_MAX_SIZE_MB", None)
    
    def test_upload_returns_file_size(self, client: TestClient):
        """Test that upload response includes file size."""
        test_content = b"test file content"
        response = client.post(
            "/upload",
            files={"file": ("test.txt", io.BytesIO(test_content), "text/plain")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "file_size_bytes" in data
        assert data["file_size_bytes"] == len(test_content)
    
    def test_upload_list(self, client: TestClient):
        """Test listing uploads."""
        response = client.get("/upload")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_upload_status(self, client: TestClient, sample_csv_file: Path):
        """Test getting upload status."""
        # Upload a file first
        with open(sample_csv_file, "rb") as f:
            upload_response = client.post(
                "/upload",
                files={"file": ("test_spins.csv", f, "text/csv")}
            )
        
        upload_id = upload_response.json()["upload_id"]
        
        # Get upload status
        response = client.get(f"/upload/{upload_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == upload_id
        assert "status" in data
    
    def test_upload_status_not_found(self, client: TestClient):
        """Test getting status of nonexistent upload."""
        response = client.get("/upload/99999/status")
        
        assert response.status_code == 404
    
    def test_download_csv_template_spin(self, client: TestClient):
        """Test downloading spin CSV template."""
        response = client.get("/upload/template/spin")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv"
        content = response.text
        assert "timestamp" in content or "bet_amount" in content
    
    def test_download_csv_template_session(self, client: TestClient):
        """Test downloading session CSV template."""
        response = client.get("/upload/template/session")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv"
        content = response.text
        assert "session" in content.lower() or "game" in content.lower()
    
    def test_download_csv_template_invalid(self, client: TestClient):
        """Test downloading invalid template type."""
        response = client.get("/upload/template/invalid_type")
        
        assert response.status_code == 400
    
    def test_upload_rate_limiting(self, client: TestClient):
        """Test that upload endpoint is rate-limited."""
        # Attempt multiple uploads rapidly
        for i in range(11):  # Exceed the 10 req/min limit
            response = client.post(
                "/upload",
                files={"file": (f"test{i}.txt", io.BytesIO(b"content"), "text/plain")}
            )
            
            if i < 10:
                # First 10 should succeed
                assert response.status_code in [200, 415]  # 415 for unsupported type
            else:
                # 11th should be rate-limited
                assert response.status_code == 429
    
    def test_virus_scan_graceful_degradation(self, client: TestClient):
        """Test that upload proceeds even when ClamAV is unavailable."""
        # This test assumes ClamAV is not running in test environment
        test_content = b"test file for virus scan"
        response = client.post(
            "/upload",
            files={"file": ("test.txt", io.BytesIO(test_content), "text/plain")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "virus_scan" in data
        # Should indicate scan was skipped or unavailable
        assert "skip" in data["virus_scan"].lower() or "unavailable" in data["virus_scan"].lower()
    
    def test_upload_video_file(self, client: TestClient):
        """Test uploading a video file (simulated)."""
        # Create a fake video file
        video_content = b"fake video content for testing"
        response = client.post(
            "/upload",
            files={"file": ("test.mp4", io.BytesIO(video_content), "video/mp4")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["file_type"] == "video"
        assert data["status"] == "processing"  # Videos need frame extraction