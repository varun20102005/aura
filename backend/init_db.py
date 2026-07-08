from app.database import engine, Base, SessionLocal
from app.models.core import User
from app.services.auth_service import get_password_hash

def init_db():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "admin@aura.com").first():
            print("Creating default admin user...")
            admin = User(
                email="admin@aura.com", 
                hashed_password=get_password_hash("admin"), 
                role="Admin"
            )
            db.add(admin)
            db.commit()
            print("Admin user created (email: admin@aura.com, pass: admin)")
        else:
            print("Admin user already exists.")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
