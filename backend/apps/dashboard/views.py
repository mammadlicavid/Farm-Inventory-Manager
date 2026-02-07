from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    context = {
        'user_name': 'Əli',
        'stats': {
            'new_harvest': 12,
            'expenses': 450,
            'animals': 5,
        }
    }
    return render(request, 'dashboard/index.html', context)
