from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from .models import UserSettings


@login_required
def profile_view(request):
    if request.method == 'POST':
        user            = request.user
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name  = request.POST.get('last_name',  '').strip()
        user.email      = request.POST.get('email',      '').strip()
        user.save()
        messages.success(request, 'Profil məlumatları uğurla yeniləndi.')
        return redirect('sidebar_menu:profile')
    return render(request, 'sidebar_menu/profile.html')


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Şifrəniz uğurla dəyişdirildi.')
        else:
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
    return redirect('sidebar_menu:profile')


@login_required
def setting_view(request):
    settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        settings_obj.language             = request.POST.get('language', 'az')
        settings_obj.timezone             = request.POST.get('timezone', 'Asia/Baku')
        settings_obj.unit                 = request.POST.get('unit',     'kg')
        settings_obj.currency             = request.POST.get('currency', 'AZN')
        settings_obj.email_notifications  = 'email_notifications'  in request.POST
        settings_obj.system_notifications = 'system_notifications' in request.POST
        settings_obj.save()
        messages.success(request, 'Parametrlər uğurla yadda saxlanıldı.')
        return redirect('sidebar_menu:setting')
    return render(request, 'sidebar_menu/setting.html', {'user_settings': settings_obj})


@login_required
def help_view(request):
    return render(request, 'sidebar_menu/help.html')