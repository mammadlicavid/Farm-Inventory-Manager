import secrets
from datetime import timedelta
from typing import Any, Dict, Optional

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
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


def send_html_email(subject: str, to_email: str, html_content: str) -> None:
    if settings.EMAIL_BACKEND.endswith("smtp.EmailBackend") and (
        not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD
    ):
        raise ImproperlyConfigured("SMTP email ayarlari tamamlanmayib.")
    text_content = strip_tags(html_content)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    message.attach_alternative(html_content, "text/html")
    message.send(fail_silently=False)


def build_email_shell(title: str, intro: str, accent: str, body_lines: list[str], footer: str) -> str:
    context = {
        "title": title,
        "intro": intro,
        "accent": accent,
        "body_lines": body_lines,
        "footer": footer,
        "app_name": _("Ferma İdarəsi"),
    }
    return render_to_string("registration/email_shell.html", context)


def send_verification_email(to_email: str, code: str, expires_minutes: int = 3) -> None:
    html_content = build_email_shell(
        title=_("E-poçt təsdiqi"),
        intro=_("E-poçt ünvanınızı təsdiqləmək üçün aşağıdakı kodu istifadə edin."),
        accent=code,
        body_lines=[
            _("Kod yalnız %(minutes)s dəqiqə aktivdir.") % {"minutes": expires_minutes},
            _("Əgər bu sorğunu siz etməmisinizsə, bu emailə məhəl qoymayın."),
        ],
        footer=_("Kod bitməmiş onu tətbiqdə daxil edin."),
    )
    send_html_email(_("Ferma İdarəsi - E-poçt təsdiq kodu"), to_email, html_content)


def send_account_notification_email(user: User, to_email: str, *, is_email_change: bool = False) -> None:
    intro = (
        _("Hesabınız uğurla yaradıldı və istifadəyə hazırdır.")
        if not is_email_change
        else _("Bu e-poçt ünvanı hesabınıza uğurla əlavə edildi.")
    )
    html_content = build_email_shell(
        title=_("Hesab məlumatı"),
        intro=intro,
        accent=user.username,
        body_lines=[
            _("İstifadəçi adı: %(username)s") % {"username": user.username},
            _("Ad: %(name)s")
            % {"name": user.get_full_name().strip() or user.username},
            _("Tarix: %(date)s") % {"date": timezone.localtime().strftime("%d.%m.%Y %H:%M")},
        ],
        footer=_("Bu məlumatı təhlükəsiz saxlayın."),
    )
    send_html_email(_("Ferma İdarəsi - Hesab məlumatı"), to_email, html_content)


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
    send_verification_email(normalized_email, verification.code)
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
