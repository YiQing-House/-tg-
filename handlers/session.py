
# Global Set to store active sessions (cleared on restart)
active_sessions = set()

def is_session_active(user_id):
    return user_id in active_sessions

def activate_session(user_id):
    active_sessions.add(user_id)
