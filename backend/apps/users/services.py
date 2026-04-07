import secrets
from datetime import timedelta
from typing import Any, Dict, Optional

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext as _

from .models import EmailVerification, UserProfile

def auth_api_login(username: str, password: str) -> Dict[str, Any]:
    user = authenticate(username=username, password=password)
    if user is not None:
        return {"code": 0, "message": "Success", "user": user}

    return {"code": 1, "message": "Wrong username or password."}


def get_or_create_profile(user: User) -> UserProfile:
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"birth_date": timezone.localdate()},
    )
    return profile


def generate_email_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def create_email_verification(*, email: str, purpose: str, user: Optional[User] = None) -> EmailVerification:
    normalized_email = email.strip().lower()
    EmailVerification.objects.filter(
        email__iexact=normalized_email,
        purpose=purpose,
        user=user,
        verified_at__isnull=True,
    ).delete()
    verification = EmailVerification.objects.create(
        user=user,
        email=normalized_email,
        purpose=purpose,
        code=generate_email_code(),
        expires_at=timezone.now() + timedelta(minutes=3),
    )
    return verification


def verify_email_code(*, email: str, purpose: str, code: str, user: Optional[User] = None) -> EmailVerification:
    verification = (
        EmailVerification.objects.filter(
            email__iexact=email.strip().lower(),
            purpose=purpose,
            user=user,
            verified_at__isnull=True,
        )
        .order_by("-created_at")
        .first()
    )
    if verification is None:
        raise ValueError(_("Aktiv təsdiq sorğusu tapılmadı."))
    if verification.is_expired:
        raise ValueError(_("Təsdiq kodunun vaxtı bitib."))
    if verification.code != code.strip():
        raise ValueError(_("Təsdiq kodu yanlışdır."))
    verification.verified_at = timezone.now()
    verification.save(update_fields=["verified_at"])
    return verification
