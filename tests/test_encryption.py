import pytest
import tempfile
import os
from pathlib import Path
from database.encryption import (
    derive_encryption_key,
    SQLCIPHER_AVAILABLE,
)


class TestKeyDerivation:
    def test_derives_deterministic_key(self):
        salt = b"\x00" * 16
        key1, _ = derive_encryption_key("password", salt)
        key2, _ = derive_encryption_key("password", salt)
        assert key1 == key2

    def test_different_passwords_different_keys(self):
        salt = b"\x00" * 16
        key1, _ = derive_encryption_key("password1", salt)
        key2, _ = derive_encryption_key("password2", salt)
        assert key1 != key2

    def test_different_salts_different_keys(self):
        key1, _ = derive_encryption_key("password")
        key2, _ = derive_encryption_key("password")
        assert key1 != key2

    def test_key_is_32_bytes(self):
        key, _ = derive_encryption_key("password")
        assert len(key) == 32


class TestSqlcipherAvailability:
    def test_check_returns_boolean(self):
        assert isinstance(SQLCIPHER_AVAILABLE, bool)


# Only run these tests if pysqlcipher3 is installed
@pytest.mark.skipif(not SQLCIPHER_AVAILABLE, reason="pysqlcipher3 not installed")
class TestEncryptedConnection:
    def test_create_encrypted_db(self, tmp_path):
        from database.encryption import create_encrypted_connection
        db_path = str(tmp_path / "test.db")
        conn = create_encrypted_connection(db_path, "testpassword")
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'hello')")
        conn.commit()
        conn.close()

        # Reopen with same password
        conn2 = create_encrypted_connection(db_path, "testpassword")
        row = conn2.execute("SELECT val FROM test WHERE id=1").fetchone()
        assert row["val"] == "hello"
        conn2.close()

    def test_wrong_password_fails(self, tmp_path):
        from database.encryption import create_encrypted_connection
        db_path = str(tmp_path / "test.db")
        conn = create_encrypted_connection(db_path, "correct_password")
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        with pytest.raises(ValueError, match="Wrong password"):
            create_encrypted_connection(db_path, "wrong_password")
