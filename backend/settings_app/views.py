from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


@login_required
def settings_page(request):
    settings = request.user.settings

    if request.method == "POST":
        settings.big_text = request.POST.get("big_text") == "on"
        settings.auto_sync = request.POST.get("auto_sync") == "on"
        settings.unit = request.POST.get("unit", settings.unit)
        settings.currency = request.POST.get("currency", settings.currency)
        settings.save()

        return redirect("settings:page")

    return render(request, "settings_app/settings_app.html", {
        "settings": settings
    })