from database import db
import config

try:
    uid = int(config.ADMIN_ID)
    print(f"Resetting terms for Admin ID: {uid}")
    
    # Check if user exists first
    user = db.get_user(uid)
    if not user:
        print("User not found, adding...")
        db.add_user(uid, "Admin", "AdminUser")
        
    db.update_user_terms(uid, False)
    print("✅ Successfully reset terms status to FALSE.")
except Exception as e:
    print(f"❌ Error: {e}")
