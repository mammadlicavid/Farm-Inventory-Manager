from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from users.models import UserProfile


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SignUpFlowTests(TestCase):
    def test_signup_creates_active_user_and_profile(self):
        response = self.client.post(
            reverse("process_signup"),
            {
                "first_name": "Ali",
                "last_name": "",
                "birth_date": "1999-05-10",
                "username": "ali99",
                "email": "ali@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertRedirects(response, reverse("login"))
        user = User.objects.get(username="ali99")
        self.assertEqual(user.first_name, "Ali")
        self.assertEqual(user.email, "ali@example.com")
        self.assertTrue(user.is_active)
        self.assertEqual(user.profile.birth_date.isoformat(), "1999-05-10")
        self.assertEqual(len(mail.outbox), 1)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ProfileFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="murad",
            email="murad@old.com",
            password="StrongPass123!",
            first_name="Murad",
        )
        UserProfile.objects.create(user=self.user, birth_date="1995-06-15")
        self.client.force_login(self.user)

    def test_profile_email_can_be_saved_without_verification(self):
        response = self.client.post(
            reverse("sidebar_menu:profile"),
            {
                "first_name": "Murad",
                "last_name": "B",
                "birth_date": "1995-06-16",
                "username": "murad",
                "email": "murad@new.com",
            },
        )

        self.assertRedirects(response, reverse("sidebar_menu:profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "murad@new.com")
        self.assertEqual(self.user.last_name, "B")
        self.assertEqual(self.user.profile.birth_date.isoformat(), "1995-06-16")
        self.assertEqual(len(mail.outbox), 1)
