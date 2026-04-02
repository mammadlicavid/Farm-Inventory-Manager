from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from .models import UserProfile


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(required=True, label=_("Ad"))
    last_name = forms.CharField(required=False, label=_("Soyad"))
    birth_date = forms.DateField(
        required=True,
        label=_("Doğum günü"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("first_name", "last_name", "birth_date", "username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            "first_name": _("Adınızı yazın"),
            "last_name": _("Soyadınızı yazın"),
            "birth_date": _("Doğum gününü seçin"),
            "username": _("İstifadəçi adı"),
            "email": _("E-poçt ünvanı"),
            "password1": _("Şifrə"),
            "password2": _("Şifrəni təkrarlayın"),
        }
        for name, field in self.fields.items():
            css_class = "form-input"
            field.widget.attrs.setdefault("class", css_class)
            field.widget.attrs.setdefault("placeholder", placeholders.get(name, ""))

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("Bu e-poçt artıq istifadə olunur."))
        return email

    def clean_first_name(self):
        return self.cleaned_data["first_name"].strip()

    def clean_last_name(self):
        return self.cleaned_data["last_name"].strip()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            UserProfile.objects.update_or_create(
                user=user,
                defaults={"birth_date": self.cleaned_data["birth_date"]},
            )
        return user
