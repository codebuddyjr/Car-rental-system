from db import get_db_connection
from werkzeug.security import generate_password_hash

def create_admin_user():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # First check if admin already exists
        cur.execute("SELECT License_No FROM User WHERE Email = 'admin@example.com'")
        if cur.fetchone():
            print("Admin user already exists")
            return

        # Create admin user
        cur.execute("""
            INSERT INTO User 
            (License_No, FName, LName, Email, Address, DOB, User_Type)
            VALUES 
            ('ADMIN001', 'System', 'Admin', 'admin@example.com', 'Admin Office', '1990-01-01', 'Admin')
        """)

        # Create admin credentials
        hashed_password = generate_password_hash('admin123')
        cur.execute("""
            INSERT INTO User_Credential 
            (License_No, Password, Year_Of_Membership)
            VALUES 
            ('ADMIN001', %s, YEAR(CURDATE()))
        """, (hashed_password,))

        # Add phone number
        cur.execute("""
            INSERT INTO User_Phone
            (License_No, Phone)
            VALUES
            ('ADMIN001', '0000000000')
        """)

        conn.commit()
        print("Admin user created successfully!")
        print("Login credentials:")
        print("Email: admin@example.com")
        print("Password: admin123")

    except Exception as e:
        conn.rollback()
        print(f"Error creating admin user: {str(e)}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    create_admin_user()