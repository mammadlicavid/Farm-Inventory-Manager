from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from typing import Dict, Any

def auth_api_login(username: str, password: str) -> Dict[str, Any]:
    # First: try to authenticate (checks username + password)
    user = authenticate(username=username, password=password)
    if user is not None:
        # Credentials correct; now check approval
        if not user.is_active:
            return {"code": 1, "message": "Your account is pending admin approval."}
        return {"code": 0, "message": "Success", "user": user}

    # If authenticate failed, we still want to detect “user exists but inactive”
    # BUT: we can only check that if username exists.
    try:
        u = User.objects.get(username=username)
        if not u.is_active:
            # username exists, and is inactive (not approved yet)
            return {"code": 1, "message": "Your account is pending admin approval."}
    except User.DoesNotExist:
        pass

    return {"code": 1, "message": "Wrong username or password."}
