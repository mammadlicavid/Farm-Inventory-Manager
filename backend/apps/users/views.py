from django.contrib.auth import login, logout
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie

from .services import auth_api_login 
from .forms import SignUpForm


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

    result = auth_api_login(username, password)

    if result["code"] == 0:
        login(request, result["user"])
        return redirect("dashboard")

    messages.error(request, result["message"])
    return redirect("login")

def logout_view(request):
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
    user.is_active = False  # admin approval required
    user.save()

    messages.success(
        request,
        "Account created. Please wait for admin approval."
    )
    return redirect("login")