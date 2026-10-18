from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import Base, get_db
from app.main import app
from app.models.user import User
from app.api.routes import profile as profile_route


def test_profile_access_update_and_admin_photo_controls(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'profile-test.db'}")
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(profile_route, "PHOTO_DIRECTORY", tmp_path / "private" / "photos")
    try:
        with TestClient(app) as client:
            assert client.get("/api/profile").status_code == 401
            assert client.get("/api/profile/theme").status_code == 401
            assert client.patch("/api/profile", json={"name": "Guest", "email": "guest@example.com"}).status_code == 401
            client.post("/api/auth/register", json={"name": "Regular", "email": "regular@example.com", "password": "SafePassword123!"})
            client.post("/api/auth/register", json={"name": "Admin", "email": "admin-photo@example.com", "password": "SafePassword123!"})
            with Session(engine) as db:
                admin = db.query(User).filter_by(email="admin-photo@example.com").one()
                admin.role = "admin"
                db.commit()

            def auth(email):
                result = client.post("/api/auth/login", json={"email": email, "password": "SafePassword123!"})
                return {"Authorization": f"Bearer {result.json()['access_token']}"}

            regular_headers = auth("regular@example.com")
            admin_headers = auth("admin-photo@example.com")
            assert client.get("/api/profile", headers=regular_headers).json()["role"] == "user"
            assert client.get("/api/profile/theme", headers=regular_headers).json() == {"theme": "system"}
            assert client.get("/api/profile/theme", headers=admin_headers).json() == {"theme": "system"}
            assert client.patch("/api/profile", headers=regular_headers, json={"name": "", "email": "not-an-email"}).status_code == 422
            assert client.put("/api/profile/theme", headers=regular_headers, json={"theme": "sepia"}).status_code == 422
            saved_theme = client.put("/api/profile/theme", headers=regular_headers, json={"theme": "dark"})
            assert saved_theme.status_code == 200
            regular_headers = {"Authorization": f"Bearer {saved_theme.json()['access_token']}"}
            assert client.get("/api/profile/theme", headers=regular_headers).json() == {"theme": "dark"}
            assert client.get("/api/profile/theme", headers=admin_headers).json() == {"theme": "system"}
            changed_profile = client.patch("/api/profile", headers=regular_headers, json={"name": "Updated", "email": "updated@example.com"})
            assert changed_profile.json()["name"] == "Updated"
            regular_headers = {"Authorization": f"Bearer {changed_profile.json()['access_token']}"}
            persisted_profile = client.get("/api/profile", headers=regular_headers)
            assert persisted_profile.status_code == 200
            assert persisted_profile.json()["name"] == "Updated"
            assert persisted_profile.json()["email"] == "updated@example.com"
            assert client.post("/api/profile/photo", headers=regular_headers, files={"file": ("photo.png", b"\x89PNG\r\n\x1a\nimage", "image/png")}).status_code == 403

            invalid = client.post("/api/profile/photo", headers=admin_headers, files={"file": ("fake.png", b"not an image", "image/png")})
            assert invalid.status_code == 415
            oversize = client.post("/api/profile/photo", headers=admin_headers, files={"file": ("large.png", b"\x89PNG\r\n\x1a\n" + b"x" * (5 * 1024 * 1024), "image/png")})
            assert oversize.status_code == 413
            uploaded = client.post("/api/profile/photo", headers=admin_headers, files={"file": ("../../avatar.png", b"\x89PNG\r\n\x1a\nvalid", "image/png")})
            assert uploaded.status_code == 200
            assert uploaded.json()["profile_photo_available"] is True
            admin_headers = {"Authorization": f"Bearer {uploaded.json()['access_token']}"}
            private_photo = client.get("/api/profile/photo", headers=admin_headers)
            assert private_photo.status_code == 200
            assert private_photo.headers["cache-control"] == "private, no-store"
            assert client.get("/api/profile/photo", headers=regular_headers).status_code == 404
            client.post("/api/auth/logout", headers=regular_headers)
            relogin_headers = auth("updated@example.com")
            assert client.get("/api/profile/theme", headers=relogin_headers).json() == {"theme": "dark"}
            removed = client.delete("/api/profile/photo", headers=admin_headers)
            assert removed.status_code == 200
            assert removed.json()["profile_photo_available"] is False
            admin_headers = {"Authorization": f"Bearer {removed.json()['access_token']}"}
            assert client.get("/api/profile/photo", headers=admin_headers).status_code == 404
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()
