from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    birth_date = models.DateField(_("Doğum günü"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("İstifadəçi profili")
        verbose_name_plural = _("İstifadəçi profilləri")

    def __str__(self):
        return f"{self.user.username} profile"


class EmailVerification(models.Model):
    PURPOSE_SIGNUP = "signup"
    PURPOSE_PROFILE = "profile_email"
    PURPOSE_CHOICES = [
        (PURPOSE_SIGNUP, _("Qeydiyyat")),
        (PURPOSE_PROFILE, _("Profil e-poçtu")),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verifications",
        null=True,
        blank=True,
    )
    email = models.EmailField(_("E-poçt"))
    purpose = models.CharField(_("Təyinat"), max_length=32, choices=PURPOSE_CHOICES)
    code = models.CharField(_("Kod"), max_length=6)
    expires_at = models.DateTimeField(_("Bitmə vaxtı"))
    verified_at = models.DateTimeField(_("Təsdiq vaxtı"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "purpose"]),
            models.Index(fields=["user", "purpose"]),
        ]
        verbose_name = _("E-poçt təsdiqi")
        verbose_name_plural = _("E-poçt təsdiqləri")

    def __str__(self):
        return f"{self.email} ({self.purpose})"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at
