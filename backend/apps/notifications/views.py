from django.utils.translation import gettext_lazy as _
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from datetime import timedelta
from django.core.cache import cache
import json

from .models import Notification, StockAlertRule
from .services import build_stock_alerts, build_stock_rule_catalog, sync_stock_alert_notifications


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


def _clear_dashboard_cache(user):
    now = timezone.localtime(timezone.now())
    start_of_week = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    cache.delete(f"dashboard:v4:{user.pk}:{start_of_week.date().isoformat()}")


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
                _clear_dashboard_cache(request.user)
                messages.success(request, f'"{title}" xatırlatması əlavə edildi.')
            else:
                messages.error(request, _("Başlıq və tarix tələb olunur."))

        elif action == 'toggle':
            notif_id = request.POST.get('notif_id')
            notif = get_object_or_404(Notification, pk=notif_id, created_by=request.user)
            notif.is_completed = not notif.is_completed
            notif.save()
            _clear_dashboard_cache(request.user)

        elif action == 'delete':
            notif_id = request.POST.get('notif_id')
            notif = get_object_or_404(Notification, pk=notif_id, created_by=request.user)
            notif.delete()
            _clear_dashboard_cache(request.user)
            messages.success(request, _("Xatırlatma silindi."))

        elif action == 'add_stock_rule':
            item_key = request.POST.get('item_key', '').strip()
            threshold_raw = request.POST.get('threshold', '').strip()

            stock_alerts, stock_items, _rule_map = build_stock_alerts(request.user)
            del stock_alerts, _rule_map
            stock_map = {item['item_key']: item for item in stock_items}
            stock_item = stock_map.get(item_key)

            if not stock_item:
                messages.error(request, _("Seçilmiş məhsul tapılmadı."))
            elif not threshold_raw:
                messages.error(request, _("Xəbərdarlıq həddi tələb olunur."))
            else:
                try:
                    threshold = Decimal(threshold_raw)
                except (InvalidOperation, TypeError, ValueError):
                    threshold = Decimal("0")

                if threshold <= 0:
                    messages.error(request, _("Xəbərdarlıq həddi 0-dan böyük olmalıdır."))
                else:
                    StockAlertRule.objects.update_or_create(
                        created_by=request.user,
                        item_key=item_key,
                        defaults={
                            'source_type': stock_item['source_type'],
                            'item_name': stock_item['item_name'],
                            'unit': stock_item['unit'],
                            'threshold': threshold,
                            'is_active': True,
                        },
                    )
                    _clear_dashboard_cache(request.user)
                    messages.success(
                        request,
                        _('"{name}" üçün ehtiyat xəbərdarlığı yeniləndi.').format(
                            name=stock_item['item_name']
                        ),
                    )

        elif action == 'delete_stock_rule':
            rule_id = request.POST.get('rule_id')
            rule = get_object_or_404(StockAlertRule, pk=rule_id, created_by=request.user)
            rule.delete()
            _clear_dashboard_cache(request.user)
            messages.success(request, _('Ehtiyat xəbərdarlığı silindi.'))

        return redirect('notifications:list')

    # GET — build context
    generated_alerts, _pending_notification_count = sync_stock_alert_notifications(request.user)
    user_notifications = Notification.objects.filter(
        created_by=request.user,
    ).exclude(
        is_system_generated=True,
        category='ehtiyat',
    )

    pending = user_notifications.filter(is_completed=False).order_by('due_date')
    completed = user_notifications.filter(is_completed=True).order_by('-due_date')

    # Attach relative date strings
    for notif in pending:
        notif.relative_date = _relative_date(notif.due_date)
    for notif in completed:
        notif.relative_date = _relative_date(notif.due_date)

    stock_alerts, stock_items, rule_map = build_stock_alerts(request.user)
    if generated_alerts:
        stock_alerts = generated_alerts
    stock_rule_catalog = build_stock_rule_catalog(stock_items)
    stock_item_map = {item['item_key']: item for item in stock_items}
    stock_alert_rules = [
        {
            'id': rule.id,
            'item_key': rule.item_key,
            'item_name': rule.item_name,
            'source_label': next(
                label for value, label in StockAlertRule.SOURCE_CHOICES if value == rule.source_type
            ),
            'threshold': rule.threshold,
            'unit': rule.unit,
            'current_total': stock_item_map[rule.item_key]['total_display']
            if rule.item_key in stock_item_map else None,
        }
        for rule in rule_map.values()
    ]
    stock_alert_rules.sort(key=lambda rule: rule['item_name'].lower())

    context = {
        'pending': pending,
        'completed': completed,
        'pending_count': pending.count(),
        'completed_count': completed.count(),
        'category_choices': Notification.CATEGORY_CHOICES,
        'stock_alerts': stock_alerts,
        'stock_alert_count': len(stock_alerts),
        'stock_items': stock_items,
        'stock_rule_catalog': stock_rule_catalog,
        'stock_rule_catalog_json': json.dumps(stock_rule_catalog, ensure_ascii=False),
        'stock_alert_rules': stock_alert_rules,
    }

    return render(request, 'notifications/notifications.html', context)
