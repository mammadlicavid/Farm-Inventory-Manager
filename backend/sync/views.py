from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

@login_required
def sync_page(request):
    context = {
        "last_sync": timezone.now(),
    }
    return render(request, "sync/sync_page.html", context)