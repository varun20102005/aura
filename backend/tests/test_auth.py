def test_register_user(client):
    response = client.post("/auth/register", json={
        "email": "newuser@test.com",
        "password": "password123",
        "role": "Investigator"
    })
    assert response.status_code == 200
    assert response.json() == {"message": "User registered successfully"}

def test_login_user(client):
    response = client.post("/auth/login", data={
        "username": "newuser@test.com",
        "password": "password123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_protected_route_without_token(client):
    response = client.get("/admin/dashboard/analytics")
    assert response.status_code == 401

def test_protected_route_with_token(client, admin_token):
    response = client.get(
        "/admin/dashboard/analytics",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
