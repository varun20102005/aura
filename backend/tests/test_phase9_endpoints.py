import pytest
from app.models.core import Notification
from app.services.auth_service import create_access_token

def test_get_notifications_happy(client, admin_token, db):
    # Setup user and token
    from app.models.core import User
    from app.services.auth_service import get_password_hash
    test_user = User(id=99, email="notif@test.com", hashed_password=get_password_hash("pass"), role="Investigator")
    db.merge(test_user)
    db.commit()
    token = create_access_token(data={"sub": test_user.email, "role": test_user.role})

    # Add notification for user
    notif = Notification(recipient_id=99, type="TEST", payload={"msg": "Hello"})
    db.add(notif)
    db.commit()

    res = client.get("/notifications", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["type"] == "TEST"

def test_get_notifications_unauth(client):
    res = client.get("/notifications")
    assert res.status_code == 401

def test_read_notification_happy(client, admin_token, db):
    # create one for admin
    # Need to find admin id
    from app.models.core import User
    admin = db.query(User).filter_by(role="Admin").first()
    notif = Notification(id=10, recipient_id=admin.id, type="TEST", payload={"msg": "Hello"})
    db.merge(notif)
    db.commit()

    res = client.post("/notifications/10/read", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200

def test_read_notification_not_found(client, admin_token):
    res = client.post("/notifications/999/read", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 404

def test_read_notification_unauth(client):
    res = client.post("/notifications/1/read")
    assert res.status_code == 401

def test_read_notification_rbac(client, db):
    # Try reading someone else's notification
    from app.models.core import User
    from app.services.auth_service import get_password_hash
    other_user = User(id=101, email="other@test.com", hashed_password=get_password_hash("pass"), role="Investigator")
    db.merge(other_user)
    db.commit()
    token = create_access_token(data={"sub": other_user.email, "role": other_user.role})
    
    # Assume notification 10 belongs to user 100
    res = client.post("/notifications/10/read", headers={"Authorization": f"Bearer {token}"})
    # Depending on implementation, might be 403 or 404
    assert res.status_code in [403, 404]
