from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie

from .forms import SignUpForm
from .models import UserProfile
from .services import send_account_notification_email
from common.messages import add_crud_success_message

# Create your views here.

@never_cache
@ensure_csrf_cookie
def login_page(request):
    return render(request, "registration/login.html")


def process_login(request):
    if request.method != "POST":
        return redirect("login")

    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "")

    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        request.session["session_start"] = timezone.now().isoformat()
        return redirect("dashboard")

    messages.error(request, _("İstifadəçi adı və ya şifrə səhvdir."))
    return redirect("login")

def logout_view(request):
    request.session.pop("session_start", None)    
    logout(request)
    return redirect("login")

@never_cache
@ensure_csrf_cookie
def signup_page(request):
    # GET: show the signup form
    form = SignUpForm()
    return render(request, "registration/signup.html", {"form": form})


def process_signup(request):
    # POST: handle signup
    if request.method != "POST":
        return redirect("signup")

    form = SignUpForm(request.POST)
    if not form.is_valid():
        # show form errors
        return render(request, "registration/signup.html", {"form": form})

    user = form.save(commit=False)
    user.is_active = True
    user.save()
    UserProfile.objects.update_or_create(
        user=user,
        defaults={"birth_date": form.cleaned_data["birth_date"]},
    )
    try:
        send_account_notification_email(user, form.cleaned_data["email"])
    except Exception:
        messages.warning(request, _("Hesab yaradıldı, amma bildiriş emaili göndərilmədi."))

    add_crud_success_message(request, "Account", "create")
    return redirect("login")
