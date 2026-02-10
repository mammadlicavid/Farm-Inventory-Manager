import os
import sys

# Configure settings for Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Setup django
import django
django.setup()

from django.contrib.auth import get_user_model

def create_admin():
    User = get_user_model()
    username = "admin"
    password = "admin123"
    email = "admin@example.com"
    
    try:
        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        if created:
            user.set_password(password)
            user.is_superuser = True
            user.is_staff = True
            user.save()
            print("SUCCESS: User 'admin' created with password 'admin123'")
        else:
            # Update password if user exists
            user.set_password(password)
            user.is_superuser = True
            user.is_staff = True
            user.save()
            print("SUCCESS: User 'admin' already exists. Password reset to 'admin123'")
            
    except Exception as e:
        print(f"ERROR: Failed to create user. {str(e)}")

if __name__ == "__main__":
    create_admin()
