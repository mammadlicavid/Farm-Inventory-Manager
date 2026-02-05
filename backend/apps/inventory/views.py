from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

def home(request):
    return HttpResponse("Home page")

@login_required
def dashboard(request):
    return HttpResponse("Dashboard ✅ You are logged in.")
