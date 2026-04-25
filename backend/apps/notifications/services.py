from decimal import Decimal

from django.core.cache import cache
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext as _

from common.templatetags.common_extras import display_quantity
from common.templatetags.common_extras import display_unit_for_user
from common.view_cache import get_dashboard_bust_value
from animals.models import Animal
from animals.models import AnimalSubCategory
from farm_products.models import FarmProduct
from farm_products.models import FarmProductItem
from seeds.models import Seed
from seeds.models import SeedItem
from tools.models import Tool
from tools.models import ToolItem

from .models import StockAlertRule


DEFAULT_THRESHOLDS = {
    "kq": Decimal("25"),
    "kg": Decimal("25"),
    "ton": Decimal("1"),
    "qram": Decimal("5000"),
    "litr": Decimal("20"),
    "ml": Decimal("1000"),
    "ədəd": Decimal("10"),
    "dəstə": Decimal("10"),
    "bağlama": Decimal("5"),
}

IMPORTANT_SEED_NAMES = {
    "Buğda toxumu",
    "Arpa toxumu",
}

IMPORTANT_FARM_PRODUCT_NAMES = {
    "Yonca",
    "Mineral gübrə",
}

IMPORTANT_FARM_PRODUCT_KEYWORDS = (
    "yem",
    "gübrə",
    "gubre",
    "yanacaq",
    "dərman",
    "derman",
)

HEADER_NOTIFICATION_COUNT_CACHE_TTL = 300
STOCK_ITEMS_CACHE_TTL = 300

SOURCE_LABELS = {
    StockAlertRule.SOURCE_SEED: _("Toxum"),
    StockAlertRule.SOURCE_TOOL: _("Alət"),
    StockAlertRule.SOURCE_FARM: _("Təsərrüfat məhsulu"),
    StockAlertRule.SOURCE_ANIMAL: _("Heyvan"),
}

SOURCE_ICONS = {
    StockAlertRule.SOURCE_SEED: "fa-wheat-awn",
    StockAlertRule.SOURCE_TOOL: "fa-wrench",
    StockAlertRule.SOURCE_FARM: "fa-box",
    StockAlertRule.SOURCE_ANIMAL: "fa-cow",
}


def _header_notification_count_cache_key(user_id: int, day_key: str | None = None) -> str:
    resolved_day_key = day_key or timezone.localdate().isoformat()
    return f"notifications:header-count:v2:{user_id}:{resolved_day_key}"


def _stock_items_cache_key(user_id: int, language_code: str) -> str:
    normalized_language = (language_code or "az").split("-")[0].lower()
    bust_value = get_dashboard_bust_value(user_id)
    return f"notifications:stock-items:v1:{user_id}:{bust_value}:{normalized_language}"


def invalidate_notification_header_count_cache(user_id: int) -> None:
    today_key = timezone.localdate().isoformat()
    cache.delete(_header_notification_count_cache_key(user_id, today_key))


def set_cached_header_notification_count(user_id: int, count: int) -> None:
    cache.set(_header_notification_count_cache_key(user_id), int(count), HEADER_NOTIFICATION_COUNT_CACHE_TTL)


def get_header_notification_count(user) -> int:
    if not getattr(user, "is_authenticated", False):
        return 0

    cached_count = cache.get(_header_notification_count_cache_key(user.pk))
    if cached_count is not None:
        return int(cached_count)

    from .models import Notification

    alerts, _stock_items, _rule_map = build_stock_alerts(user)
    pending_manual_count = Notification.objects.filter(
        created_by=user,
        is_completed=False,
    ).exclude(
        is_system_generated=True,
        category="ehtiyat",
    ).count()
    count = len(alerts) + pending_manual_count
    set_cached_header_notification_count(user.pk, count)
    return count


def _normalize_decimal(value):
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _format_quantity(value):
    normalized = _normalize_decimal(value)
    if normalized == normalized.to_integral_value():
        return int(normalized)
    return float(normalized)


def _is_important_seed(item_name):
    return (item_name or "").strip() in IMPORTANT_SEED_NAMES


def _is_important_farm_product(item_name, category_name):
    if (item_name or "").strip() in IMPORTANT_FARM_PRODUCT_NAMES:
        return True
    name = (item_name or "").strip().lower()
    return any(keyword in name for keyword in IMPORTANT_FARM_PRODUCT_KEYWORDS if keyword in {"yanacaq", "dərman", "derman"})


def _default_threshold(source_type, unit):
    unit_key = (unit or "").strip().lower()
    default = DEFAULT_THRESHOLDS.get(unit_key)
    if default is not None:
        return default
    if source_type == StockAlertRule.SOURCE_TOOL:
        return Decimal("2")
    return Decimal("10")


def _serialize_stock_item(*, source_type, item_key, item_name, unit, total, is_important):
    return {
        "source_type": source_type,
        "source_label": SOURCE_LABELS[source_type],
        "item_key": item_key,
        "item_name": _(item_name or ""),
        "unit": unit,
        "total": _normalize_decimal(total),
        "total_display": _format_quantity(total),
        "is_important": is_important,
        "icon": SOURCE_ICONS[source_type],
    }


def _manual_category_label():
    return _("Digər")


def _uses_manual_inventory_name(linked_name, manual_name):
    return bool(manual_name) and (not linked_name or str(linked_name).strip().lower() == "digər")


def _resolve_inventory_item_name(linked_name, manual_name, fallback_name):
    if _uses_manual_inventory_name(linked_name, manual_name):
        return manual_name
    return linked_name or manual_name or fallback_name


def _resolve_inventory_item_key(source_type, linked_id, linked_name, manual_name, unit):
    item_identifier = linked_id
    if _uses_manual_inventory_name(linked_name, manual_name):
        item_identifier = manual_name
    return f"{source_type}:{item_identifier or manual_name or linked_name}:{unit}"


def _category_sort_key(label):
    normalized = str(label or "").strip().lower()
    other_labels = {
        _("Digər").lower(),
        _("Other").lower(),
        _("Другое").lower(),
        "digər",
        "other",
        "другое",
    }
    return (1 if normalized in other_labels else 0, normalized)


def get_stock_items_for_user(user):
    if not getattr(user, "is_authenticated", False):
        return []

    language_code = (get_language() or "az").split("-")[0].lower()
    cache_key = _stock_items_cache_key(user.pk, language_code)
    cached_items = cache.get(cache_key)
    if cached_items is not None:
        return cached_items

    stock_items = {}

    seed_rows = (
        Seed.objects.filter(created_by=user)
        .values("item_id", "item__name", "item__category__name", "manual_name", "unit")
        .annotate(total=Sum("quantity"))
    )
    for row in seed_rows:
        item_name = _resolve_inventory_item_name(row["item__name"], row["manual_name"], "Toxum")
        item_key = _resolve_inventory_item_key(
            StockAlertRule.SOURCE_SEED,
            row["item_id"],
            row["item__name"],
            row["manual_name"],
            row["unit"] or "kg",
        )
        stock_item = _serialize_stock_item(
            source_type=StockAlertRule.SOURCE_SEED,
            item_key=item_key,
            item_name=item_name,
            unit=row["unit"] or "kg",
            total=row["total"],
            is_important=_is_important_seed(item_name),
        )
        stock_item["category_name"] = _(row.get("item__category__name") or "") or _manual_category_label()
        stock_items[item_key] = stock_item

    tool_rows = (
        Tool.objects.filter(created_by=user)
        .values("item_id", "item__name", "item__category__name", "manual_name")
        .annotate(total=Sum("quantity"))
    )
    for row in tool_rows:
        item_name = _resolve_inventory_item_name(row["item__name"], row["manual_name"], "Alət")
        item_key = _resolve_inventory_item_key(
            StockAlertRule.SOURCE_TOOL,
            row["item_id"],
            row["item__name"],
            row["manual_name"],
            "ədəd",
        )
        stock_item = _serialize_stock_item(
            source_type=StockAlertRule.SOURCE_TOOL,
            item_key=item_key,
            item_name=item_name,
            unit="ədəd",
            total=row["total"],
            is_important=False,
        )
        stock_item["category_name"] = _(row.get("item__category__name") or "") or _manual_category_label()
        stock_items[item_key] = stock_item

    animal_rows = (
        Animal.objects.filter(created_by=user)
        .values("subcategory_id", "subcategory__name", "subcategory__category__name", "manual_name")
        .annotate(total=Sum("quantity"))
    )
    for row in animal_rows:
        item_name = _resolve_inventory_item_name(row["subcategory__name"], row["manual_name"], "Heyvan")
        item_key = _resolve_inventory_item_key(
            StockAlertRule.SOURCE_ANIMAL,
            row["subcategory_id"],
            row["subcategory__name"],
            row["manual_name"],
            "ədəd",
        )
        stock_item = _serialize_stock_item(
            source_type=StockAlertRule.SOURCE_ANIMAL,
            item_key=item_key,
            item_name=item_name,
            unit="ədəd",
            total=row["total"],
            is_important=False,
        )
        stock_item["category_name"] = _(row.get("subcategory__category__name") or "") or _manual_category_label()
        stock_items[item_key] = stock_item

    tool_catalog_items = ToolItem.objects.select_related("category")
    for item in tool_catalog_items:
        item_key = f"tool:{item.id}:ədəd"
        stock_items.setdefault(
            item_key,
            {
                **_serialize_stock_item(
                    source_type=StockAlertRule.SOURCE_TOOL,
                    item_key=item_key,
                    item_name=item.name,
                    unit="ədəd",
                    total=Decimal("0"),
                    is_important=False,
                ),
                "category_name": _(item.category.name) if item.category else _manual_category_label(),
            },
        )

    animal_catalog_items = AnimalSubCategory.objects.select_related("category")
    for item in animal_catalog_items:
        item_key = f"animal:{item.id}:ədəd"
        stock_items.setdefault(
            item_key,
            {
                **_serialize_stock_item(
                    source_type=StockAlertRule.SOURCE_ANIMAL,
                    item_key=item_key,
                    item_name=item.name,
                    unit="ədəd",
                    total=Decimal("0"),
                    is_important=False,
                ),
                "category_name": _(item.category.name) if item.category else _manual_category_label(),
            },
        )

    farm_rows = (
        FarmProduct.objects.filter(created_by=user)
        .values("item_id", "item__name", "item__category__name", "manual_name", "unit")
        .annotate(total=Sum("quantity"))
    )
    for row in farm_rows:
        item_name = _resolve_inventory_item_name(row["item__name"], row["manual_name"], "Məhsul")
        unit = row["unit"] or "kq"
        item_key = _resolve_inventory_item_key(
            StockAlertRule.SOURCE_FARM,
            row["item_id"],
            row["item__name"],
            row["manual_name"],
            unit,
        )
        stock_item = _serialize_stock_item(
            source_type=StockAlertRule.SOURCE_FARM,
            item_key=item_key,
            item_name=item_name,
            unit=unit,
            total=row["total"],
            is_important=_is_important_farm_product(item_name, row["item__category__name"]),
        )
        stock_item["category_name"] = _(row.get("item__category__name") or "") or _manual_category_label()
        stock_items[item_key] = stock_item

    seed_catalog_items = SeedItem.objects.select_related("category")
    for item in seed_catalog_items:
        item_key = f"seed:{item.id}:kg"
        stock_items.setdefault(
            item_key,
            {
                **_serialize_stock_item(
                    source_type=StockAlertRule.SOURCE_SEED,
                    item_key=item_key,
                    item_name=item.name,
                    unit="kg",
                    total=Decimal("0"),
                    is_important=_is_important_seed(item.name),
                ),
                "category_name": _(item.category.name) if item.category else _manual_category_label(),
            },
        )

    farm_catalog_items = FarmProductItem.objects.select_related("category")
    for item in farm_catalog_items:
        category_name = _(item.category.name) if item.category else _manual_category_label()
        unit = item.unit or "kq"
        item_key = f"farm:{item.id}:{unit}"
        stock_items.setdefault(
            item_key,
            {
                **_serialize_stock_item(
                    source_type=StockAlertRule.SOURCE_FARM,
                    item_key=item_key,
                    item_name=item.name,
                    unit=unit,
                    total=Decimal("0"),
                    is_important=_is_important_farm_product(item.name, category_name),
                ),
                "category_name": category_name,
            },
        )

    result = list(stock_items.values())
    result.sort(key=lambda item: (item["source_label"].lower(), item["category_name"].lower(), item["item_name"].lower()))
    cache.set(cache_key, result, STOCK_ITEMS_CACHE_TTL)
    return result


def build_stock_rule_catalog(stock_items, user=None):
    source_map = {}

    for item in stock_items:
        source_type = item["source_type"]
        source_entry = source_map.setdefault(
            source_type,
            {
                "value": source_type,
                "label": item["source_label"],
                "categories": {},
            },
        )
        category_name = item.get("category_name") or _manual_category_label()
        category_entry = source_entry["categories"].setdefault(
            category_name,
            {
                "value": category_name,
                "label": category_name,
                "items": [],
            },
        )
        category_entry["items"].append(
            {
                "item_key": item["item_key"],
                "label": item["item_name"],
                "unit": item["unit"],
                "unit_label": display_unit_for_user(item.get("total_display"), item["unit"], user),
                "total_display": display_quantity(item.get("total_display"), item["unit"], user),
            }
        )

    sources = []
    for source in sorted(source_map.values(), key=lambda value: value["label"].lower()):
        categories = []
        for category in sorted(source["categories"].values(), key=lambda value: _category_sort_key(value["label"])):
            category["items"] = [
                item for item in category["items"]
                if str(item.get("label") or "").strip().lower() != "digər"
            ]
            category["items"].sort(key=lambda value: _category_sort_key(value["label"]))
            if not category["items"]:
                continue
            categories.append(category)
        source["categories"] = categories
        sources.append(source)
    return sources


def get_default_threshold_for_item(stock_item):
    return _default_threshold(
        stock_item["source_type"],
        stock_item["unit"],
    )


def _partition_stock_rules(user):
    active_rules = {}
    disabled_rule_keys = set()

    for rule in StockAlertRule.objects.filter(created_by=user):
        if rule.is_active:
            active_rules[rule.item_key] = rule
        else:
            disabled_rule_keys.add(rule.item_key)

    return active_rules, disabled_rule_keys


def build_stock_alert_rule_list(user, stock_items=None):
    stock_items = stock_items or get_stock_items_for_user(user)
    stock_item_map = {item["item_key"]: item for item in stock_items}
    active_rule_map, disabled_rule_keys = _partition_stock_rules(user)
    effective_rules = []
    seen_keys = set()

    for item_key, rule in active_rule_map.items():
        stock_item = stock_item_map.get(item_key)
        effective_rules.append(
            {
                "id": rule.id,
                "item_key": rule.item_key,
                "item_name": rule.item_name,
                "source_type": rule.source_type,
                "category_name": stock_item.get("category_name") if stock_item else "",
                "source_label": SOURCE_LABELS.get(rule.source_type, rule.get_source_type_display()),
                "threshold": rule.threshold,
                "unit": rule.unit,
                "current_total": stock_item["total_display"] if stock_item else None,
                "is_system_generated": False,
            }
        )
        seen_keys.add(item_key)

    for stock_item in stock_items:
        item_key = stock_item["item_key"]
        if (
            not stock_item["is_important"]
            or item_key in seen_keys
            or item_key in disabled_rule_keys
        ):
            continue

        effective_rules.append(
            {
                "id": None,
                "item_key": item_key,
                "item_name": stock_item["item_name"],
                "source_type": stock_item["source_type"],
                "category_name": stock_item.get("category_name") or "",
                "source_label": stock_item["source_label"],
                "threshold": get_default_threshold_for_item(stock_item),
                "unit": stock_item["unit"],
                "current_total": stock_item["total_display"],
                "is_system_generated": True,
            }
        )

    effective_rules.sort(
        key=lambda rule: (
            rule["source_label"].lower(),
            (rule.get("category_name") or "").lower(),
            rule["item_name"].lower(),
        )
    )
    return effective_rules


def build_stock_alerts(user):
    stock_items = get_stock_items_for_user(user)
    rule_map, disabled_rule_keys = _partition_stock_rules(user)
    alerts = []

    for stock_item in stock_items:
        if stock_item["item_key"] in disabled_rule_keys:
            continue

        rule = rule_map.get(stock_item["item_key"])
        if rule is None and not stock_item["is_important"]:
            continue

        threshold = rule.threshold if rule else get_default_threshold_for_item(stock_item)
        total = stock_item["total"]
        if total > threshold:
            continue

        critical_threshold = threshold * Decimal("0.5")
        status = "kritik" if total <= critical_threshold else "az"
        display_max = max(threshold * Decimal("1.5"), total, Decimal("1"))
        percentage = int((total / display_max) * 100) if display_max else 0

        alerts.append(
            {
                **stock_item,
                "threshold": threshold,
                "threshold_display": _format_quantity(threshold),
                "status": status,
                "status_text": "Kritik" if status == "kritik" else "Az qalıb",
                "color": "red" if status == "kritik" else "yellow",
                "percentage": max(0, min(100, percentage)),
                "is_custom_rule": rule is not None,
                "rule_id": rule.id if rule else None,
            }
        )

    alerts.sort(
        key=lambda item: (
            0 if item["status"] == "kritik" else 1,
            item["total"],
            item["item_name"].lower(),
        )
    )
    return alerts, stock_items, rule_map


def sync_stock_alert_notifications(user, include_details: bool = False):
    from .models import Notification

    alerts, stock_items, rule_map = build_stock_alerts(user)

    today = timezone.localdate()
    active_keys = set()

    for alert in alerts:
        source_key = alert["item_key"]
        active_keys.add(source_key)
        Notification.objects.get_or_create(
            created_by=user,
            due_date=today,
            source_key=source_key,
            is_system_generated=True,
            defaults={
                "title": f'{alert["item_name"]} ehtiyatı kritik həddə düşüb',
                "category": "ehtiyat",
                "is_completed": False,
            },
        )

    stale_notifications = Notification.objects.filter(
        created_by=user,
        is_system_generated=True,
        category="ehtiyat",
    )
    if active_keys:
        stale_notifications = stale_notifications.exclude(source_key__in=active_keys)
    stale_notifications.delete()

    pending_manual_count = Notification.objects.filter(
        created_by=user,
        is_completed=False,
    ).exclude(
        is_system_generated=True,
        category="ehtiyat",
    ).count()

    count = len(alerts) + pending_manual_count
    set_cached_header_notification_count(user.pk, count)
    if include_details:
        return alerts, count, stock_items, rule_map
    return alerts, count
