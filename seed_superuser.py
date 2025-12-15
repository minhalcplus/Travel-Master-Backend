from core.app.database import SessionLocal
from auth.models import User, Role
from auth.utils import get_password_hash
import sys
import getpass
import random

def create_superuser():
    db = SessionLocal()
    try:
        print("Create Superuser")
        print("----------------")
        
        # Read inputs from stdin if available, otherwise prompt
        if not sys.stdin.isatty():
             input_lines = sys.stdin.read().splitlines()
             if len(input_lines) >= 2:
                 email = input_lines[0].strip()
                 password = input_lines[1].strip()
                 confirm_password = password
                 phone = input_lines[2].strip() if len(input_lines) > 2 else ""
             else:
                 print("Error: Not enough input provided via stdin.")
                 return
        else:
            email = input("Email: ").strip()
            password = getpass.getpass("Password: ")
            confirm_password = getpass.getpass("Confirm Password: ")
            phone = input("Phone Number (optional, press Enter to generate random): ").strip()

        if not email:
            print("Error: Email is required.")
            return

        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"Error: User with email {email} already exists.")
            return

        if password != confirm_password:
            print("Error: Passwords do not match.")
            return

        if not phone:
             # Generate a random 10-digit number
             phone = f"{random.randint(1000000000, 9999999999)}"
        
        # Check if phone exists
        existing_phone = db.query(User).filter(User.phone == phone).first()
        if existing_phone:
             print(f"Error: User with phone {phone} already exists.")
             return

        print(f"Creating superuser with email: {email}")
        
        hashed_password = get_password_hash(password)
        
        # Create user
        new_user = User(
            email=email,
            password_hash=hashed_password,
            role=Role.super_admin,
            is_email_verified=True,
            status="active",
            username=email, 
            fullname="Super Admin",
            phone=phone
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        print(f"Superuser created successfully! ID: {new_user.id}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_superuser()
