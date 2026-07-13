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
            print("Admin user created (email: admin@aura.com, pass: admin)")
        else:
            print("Admin user already exists.")
            
        if not db.query(User).filter(User.email == "investigator@aura.com").first():
            print("Creating default investigator user...")
            investigator = User(
                email="investigator@aura.com", 
                hashed_password=get_password_hash("pass"), 
                role="Investigator"
            )
            db.add(investigator)
            print("Investigator user created (email: investigator@aura.com, pass: pass)")
            
        if not db.query(User).filter(User.email == "user@aura.com").first():
            print("Creating default normal user (Officer role)...")
            user = User(
                email="user@aura.com", 
                hashed_password=get_password_hash("pass"), 
                role="Officer"
            )
            db.add(user)
            print("Normal user created (email: user@aura.com, pass: pass)")
            
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
