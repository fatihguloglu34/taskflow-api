def test_register_and_me(client, register):
    user = register()
    r = client.get("/api/v1/users/me", headers=user["headers"])
    assert r.status_code == 200
    assert r.json()["email"] == "ali@example.com"


def test_duplicate_email(client, register):
    register()
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "ALI@example.com", "password": "password123", "full_name": "Ali"},
    )
    assert r.status_code == 409


def test_wrong_password(client, register):
    register()
    r = client.post("/api/v1/auth/login", data={"username": "ali@example.com", "password": "wrongpass"})
    assert r.status_code == 401


def test_short_password_rejected(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "a@example.com", "password": "123", "full_name": "Ali"},
    )
    assert r.status_code == 422


def test_protected_route_requires_token(client):
    assert client.get("/api/v1/users/me").status_code == 401
    r = client.get("/api/v1/users/me", headers={"Authorization": "Bearer invalid"})
    assert r.status_code == 401


def test_update_me(client, register):
    user = register()
    r = client.patch("/api/v1/users/me", json={"full_name": "Yeni Isim"}, headers=user["headers"])
    assert r.json()["full_name"] == "Yeni Isim"
