from database import db
import sys

try:
    print("Checking users table...")
    users = db.get_all_users()
    print(f"Total Users: {len(users)}")
    for u in users:
        print(f"ID: {u['id']} | Name: {u['first_name']} | Status: {u['status']}")
except Exception as e:
    print(f"Error: {e}")
