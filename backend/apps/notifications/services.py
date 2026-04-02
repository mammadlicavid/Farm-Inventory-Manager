from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

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

SOURCE_LABELS = {
    StockAlertRule.SOURCE_SEED: "Toxum",
    StockAlertRule.SOURCE_TOOL: "Alət",
    StockAlertRule.SOURCE_FARM: "Təsərrüfat məhsulu",
    StockAlertRule.SOURCE_ANIMAL: "Heyvan",
}

SOURCE_ICONS = {
    StockAlertRule.SOURCE_SEED: "fa-wheat-awn",
    StockAlertRule.SOURCE_TOOL: "fa-wrench",
    StockAlertRule.SOURCE_FARM: "fa-box",
    StockAlertRule.SOURCE_ANIMAL: "fa-cow",
}


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
        "item_name": item_name,
        "unit": unit,
        "total": _normalize_decimal(total),
        "total_display": _format_quantity(total),
        "is_important": is_important,
        "icon": SOURCE_ICONS[source_type],
    }


def _manual_category_label():
    return "Xüsusi"


def get_stock_items_for_user(user):
    stock_items = {}

    seed_rows = (
        Seed.objects.filter(created_by=user)
        .values("item_id", "item__name", "item__category__name", "manual_name", "unit")
        .annotate(total=Sum("quantity"))
    )
    for row in seed_rows:
        item_name = row["item__name"] or row["manual_name"] or "Toxum"
        item_key = f"seed:{row['item_id'] or row['manual_name'] or item_name}:{row['unit'] or 'kg'}"
        stock_item = _serialize_stock_item(
            source_type=StockAlertRule.SOURCE_SEED,
            item_key=item_key,
            item_name=item_name,
            unit=row["unit"] or "kg",
            total=row["total"],
            is_important=_is_important_seed(item_name),
        )
        stock_item["category_name"] = row.get("item__category__name") or _manual_category_label()
        stock_items[item_key] = stock_item

    tool_rows = (
        Tool.objects.filter(created_by=user)
        .values("item_id", "item__name", "item__category__name", "manual_name")
        .annotate(total=Sum("quantity"))
    )
    for row in tool_rows:
        item_name = row["item__name"] or row["manual_name"] or "Alət"
        item_key = f"tool:{row['item_id'] or row['manual_name'] or item_name}:ədəd"
        stock_item = _serialize_stock_item(
            source_type=StockAlertRule.SOURCE_TOOL,
            item_key=item_key,
            item_name=item_name,
            unit="ədəd",
            total=row["total"],
            is_important=False,
        )
        stock_item["category_name"] = row.get("item__category__name") or _manual_category_label()
        stock_items[item_key] = stock_item

    animal_rows = (
        Animal.objects.filter(created_by=user)
        .values("subcategory_id", "subcategory__name", "subcategory__category__name", "manual_name")
        .annotate(total=Sum("quantity"))
    )
    for row in animal_rows:
        item_name = row["subcategory__name"] or row["manual_name"] or "Heyvan"
        item_key = f"animal:{row['subcategory_id'] or row['manual_name'] or item_name}:ədəd"
        stock_item = _serialize_stock_item(
            source_type=StockAlertRule.SOURCE_ANIMAL,
            item_key=item_key,
            item_name=item_name,
            unit="ədəd",
            total=row["total"],
            is_important=False,
        )
        stock_item["category_name"] = row.get("subcategory__category__name") or _manual_category_label()
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
                "category_name": item.category.name if item.category else _manual_category_label(),
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
                "category_name": item.category.name if item.category else _manual_category_label(),
            },
        )

    farm_rows = (
        FarmProduct.objects.filter(created_by=user)
        .values("item_id", "item__name", "item__category__name", "manual_name", "unit")
        .annotate(total=Sum("quantity"))
    )
    for row in farm_rows:
        item_name = row["item__name"] or row["manual_name"] or "Məhsul"
        unit = row["unit"] or "kq"
        item_key = f"farm:{row['item_id'] or row['manual_name'] or item_name}:{unit}"
        stock_item = _serialize_stock_item(
            source_type=StockAlertRule.SOURCE_FARM,
            item_key=item_key,
            item_name=item_name,
            unit=unit,
            total=row["total"],
            is_important=_is_important_farm_product(item_name, row["item__category__name"]),
        )
        stock_item["category_name"] = row.get("item__category__name") or _manual_category_label()
        stock_items[item_key] = stock_item

    important_seed_items = SeedItem.objects.filter(
        name__in=IMPORTANT_SEED_NAMES
    ).select_related("category")
    for item in important_seed_items:
        if not _is_important_seed(item.name):
            continue
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
                is_important=True,
                ),
                "category_name": item.category.name if item.category else _manual_category_label(),
            },
        )

    important_farm_items = FarmProductItem.objects.filter(
        name__in=IMPORTANT_FARM_PRODUCT_NAMES
    ).select_related("category")
    for item in important_farm_items:
        if not _is_important_farm_product(item.name, item.category.name):
            continue
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
                is_important=True,
                ),
                "category_name": item.category.name if item.category else _manual_category_label(),
            },
        )

    result = list(stock_items.values())
    result.sort(key=lambda item: (item["source_label"].lower(), item["category_name"].lower(), item["item_name"].lower()))
    return result


def build_stock_rule_catalog(stock_items):
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
                "total_display": item["total_display"],
            }
        )

    sources = []
    for source in sorted(source_map.values(), key=lambda value: value["label"].lower()):
        categories = []
        for category in sorted(source["categories"].values(), key=lambda value: value["label"].lower()):
            category["items"].sort(key=lambda value: value["label"].lower())
            categories.append(category)
        source["categories"] = categories
        sources.append(source)
    return sources


def build_stock_alerts(user):
    stock_items = get_stock_items_for_user(user)
    rule_map = {
        rule.item_key: rule
        for rule in StockAlertRule.objects.filter(created_by=user, is_active=True)
    }
    alerts = []

    for stock_item in stock_items:
        rule = rule_map.get(stock_item["item_key"])
        if rule is None and not stock_item["is_important"]:
            continue

        threshold = rule.threshold if rule else _default_threshold(
            stock_item["source_type"],
            stock_item["unit"],
        )
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


def sync_stock_alert_notifications(user):
    from .models import Notification

    alerts, stock_items, rule_map = build_stock_alerts(user)
    del stock_items, rule_map

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

    pending_count = Notification.objects.filter(
        created_by=user,
        is_completed=False,
    ).count()

    return alerts, pending_count
