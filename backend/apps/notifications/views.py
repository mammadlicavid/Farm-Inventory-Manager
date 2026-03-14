from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta

from .models import Notification


def _relative_date(due_date):
    """Return a human-readable Azerbaijani relative date string."""
    today = timezone.localdate()
    delta = (due_date - today).days

    if delta < 0:
        return f"{abs(delta)} gün əvvəl"
    elif delta == 0:
        return "Bu gün"
    elif delta == 1:
        return "Sabah"
    else:
        return f"{delta} gün sonra"


@login_required
def notifications_page(request):
    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'add':
            title = request.POST.get('title', '').strip()
            category = request.POST.get('category', 'diger')
            due_date = request.POST.get('due_date', '')

            if title and due_date:
                Notification.objects.create(
                    title=title,
                    category=category,
                    due_date=due_date,
                    created_by=request.user,
                )
                messages.success(request, f'"{title}" xatırlatması əlavə edildi.')
            else:
                messages.error(request, 'Başlıq və tarix tələb olunur.')

        elif action == 'toggle':
            notif_id = request.POST.get('notif_id')
            notif = get_object_or_404(Notification, pk=notif_id, created_by=request.user)
            notif.is_completed = not notif.is_completed
            notif.save()

        elif action == 'delete':
            notif_id = request.POST.get('notif_id')
            notif = get_object_or_404(Notification, pk=notif_id, created_by=request.user)
            notif.delete()
            messages.success(request, 'Xatırlatma silindi.')

        return redirect('notifications:list')

    # GET — build context
    user_notifications = Notification.objects.filter(created_by=request.user)

    pending = user_notifications.filter(is_completed=False).order_by('due_date')
    completed = user_notifications.filter(is_completed=True).order_by('-due_date')

    # Attach relative date strings
    for notif in pending:
        notif.relative_date = _relative_date(notif.due_date)
    for notif in completed:
        notif.relative_date = _relative_date(notif.due_date)

    context = {
        'pending': pending,
        'completed': completed,
        'pending_count': pending.count(),
        'completed_count': completed.count(),
        'category_choices': Notification.CATEGORY_CHOICES,
    }

    return render(request, 'notifications/notifications.html', context)
