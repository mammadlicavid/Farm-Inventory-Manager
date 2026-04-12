from django.utils.translation import gettext_lazy as _
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.utils import translation
from django.utils.translation import gettext as _

from users.services import get_or_create_profile
from .models import UserSettings

VOICE_LANGUAGE_CHOICES = {"system", "az", "en", "ru"}


def _get_voice_language(request):
    value = (request.session.get("voice_input_language") or request.COOKIES.get("voice_input_language") or "system").strip().lower()
    return value if value in VOICE_LANGUAGE_CHOICES else "system"


@login_required
def profile_view(request):
    user = request.user
    profile = get_or_create_profile(user)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        birth_date = request.POST.get('birth_date', '').strip()

        if not username:
            messages.error(request, _('İstifadəçi adı boş ola bilməz.'))
            return render(request, 'sidebar_menu/profile.html', {'profile': profile})

        if not first_name:
            messages.error(request, _('Ad boş ola bilməz.'))
            return render(request, 'sidebar_menu/profile.html', {'profile': profile})

        if not email:
            messages.error(request, _('E-poçt boş ola bilməz.'))
            return render(request, 'sidebar_menu/profile.html', {'profile': profile})

        if not birth_date:
            messages.error(request, _('Doğum günü boş ola bilməz.'))
            return render(request, 'sidebar_menu/profile.html', {'profile': profile})

        if user.__class__.objects.exclude(pk=user.pk).filter(username__iexact=username).exists():
            messages.error(request, _('Bu istifadəçi adı artıq mövcuddur.'))
            return render(request, 'sidebar_menu/profile.html', {'profile': profile})

        if user.__class__.objects.exclude(pk=user.pk).filter(email__iexact=email).exists():
            messages.error(request, _('Bu e-poçt artıq istifadə olunur.'))
            return render(request, 'sidebar_menu/profile.html', {'profile': profile})

        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()
        profile.birth_date = birth_date
        profile.save(update_fields=['birth_date', 'updated_at'])
        messages.success(request, _('Profil məlumatları uğurla yeniləndi.'))
        return redirect('sidebar_menu:profile')
    return render(request, 'sidebar_menu/profile.html', {'profile': profile})


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, _('Şifrəniz uğurla dəyişdirildi.'))
        else:
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
    return redirect('sidebar_menu:profile')


@login_required
def setting_view(request):
    settings_obj, created = UserSettings.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        settings_obj.language             = request.POST.get('language', 'az')
        settings_obj.timezone             = request.POST.get('timezone', 'Asia/Baku')
        weight_unit = request.POST.get('weight_unit', 'kg')
        if weight_unit == 'oz':
            weight_unit = 'lb'
        volume_unit = request.POST.get('volume_unit', 'litr')
        settings_obj.unit                 = f"{weight_unit}_{volume_unit}"
        settings_obj.currency             = request.POST.get('currency', 'AZN')
        settings_obj.email_notifications  = 'email_notifications'  in request.POST
        settings_obj.system_notifications = 'system_notifications' in request.POST
        voice_language = (request.POST.get('voice_language', 'system') or 'system').strip().lower()
        if voice_language not in VOICE_LANGUAGE_CHOICES:
            voice_language = 'system'
        settings_obj.save()
        request.session["django_language"] = settings_obj.language
        request.session["user_language_pref"] = settings_obj.language
        request.session["user_timezone_pref"] = settings_obj.timezone
        request.session["voice_input_language"] = voice_language
        translation.activate(settings_obj.language)
        messages.success(request, _('Parametrlər uğurla yadda saxlanıldı.'))
        response = redirect('sidebar_menu:setting')
        response.set_cookie("voice_input_language", voice_language, max_age=60 * 60 * 24 * 365)
        return response
    unit_value = settings_obj.unit or "kg_litr"
    if unit_value == "kg":
        unit_value = "kg_litr"
    elif unit_value == "lb":
        unit_value = "lb_gallon"
    elif unit_value == "gallon":
        unit_value = "kg_gallon"
    if "_" in unit_value:
        weight_unit, volume_unit = unit_value.split("_", 1)
    else:
        weight_unit, volume_unit = "kg", "litr"
    if weight_unit == "oz":
        weight_unit = "lb"
    response = render(request, 'sidebar_menu/setting.html', {
        'user_settings': settings_obj,
        'weight_unit_value': weight_unit,
        'volume_unit_value': volume_unit,
        'voice_input_language': _get_voice_language(request),
    })
    response.set_cookie("voice_input_language", _get_voice_language(request), max_age=60 * 60 * 24 * 365)
    return response


@login_required
def help_view(request):
    return render(request, 'sidebar_menu/help.html')
