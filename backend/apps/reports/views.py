import os
import hashlib
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from functools import lru_cache
from io import BytesIO
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import get_language, gettext as _T, gettext_lazy as _, override
from common.expense_titles import translate_expense_title
from common.view_cache import get_reports_bust_value

from common.formatting import format_currency
from expenses.models import Expense, ExpenseSubCategory
from incomes.models import Income
from inventory.views import FARM_PRODUCT_NAME_TRANSLATIONS, GENERIC_OPTION_TRANSLATIONS

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    REPORTLAB_AVAILABLE = True
except ImportError:  # pragma: no cover - runtime fallback when dependency is missing
    REPORTLAB_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont

    PILLOW_AVAILABLE = True
except ImportError:  # pragma: no cover - runtime fallback when dependency is missing
    PILLOW_AVAILABLE = False


REPORT_PURPOSES = {
    "tax": {
        "label": _("Vergi hesabatı"),
        "headline": _("Vergi və rəsmi təqdimat üçün xülasə"),
        "description": _("Gəlir, xərc və xalis nəticəni seçilmiş tarix aralığı üzrə toplu göstərir."),
        "accent": "tax",
    },
    "loan": {
        "label": _("Kredit hesabatı"),
        "headline": _("Kredit müraciəti üçün maliyyə görünüşü"),
        "description": _("Dövri gəlir, xalis qazanc və satış sabitliyini göstərir."),
        "accent": "loan",
    },
}

GROUP_BY_OPTIONS = {
    "auto": _("Avtomatik"),
    "day": _("Günlük"),
    "week": _("Həftəlik"),
    "month": _("Aylıq"),
}

AZ_MONTH_NAMES = {
    1: _("Yanvar"),
    2: _("Fevral"),
    3: _("Mart"),
    4: _("Aprel"),
    5: _("May"),
    6: _("İyun"),
    7: _("İyul"),
    8: _("Avqust"),
    9: _("Sentyabr"),
    10: _("Oktyabr"),
    11: _("Noyabr"),
    12: _("Dekabr"),
}

AZ_STANDARD_VAT_RATE = Decimal("0.18")
AZ_STANDARD_VAT_RATE_PERCENT = Decimal("18.00")
AGRI_TAX_EXEMPTION_START = date(2014, 1, 1)
AGRI_TAX_EXEMPTION_END = date(2027, 1, 1)
RAW_AGRI_CATEGORY_KEYWORDS = (
    "meyvə",
    "tərəvəz",
    "göyərti",
    "taxıl",
    "yem bitkiləri",
    "bostan",
    "toxum",
    "heyvan",
    "yumurta",
)
PROCESSED_PRODUCT_KEYWORDS = (
    "pendir",
    "qatıq",
    "ayran",
    "kərə yağı",
    "qaymaq",
    "ət",
    "mumu",
    "arı südü",
    "gübrə",
    "kompost",
    "mineral",
)
REPORT_CONTEXT_CACHE_TTL = 300


def _safe_decimal(value) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _quantize_money(value) -> Decimal:
    return _safe_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _plain_number(value) -> str:
    normalized = _safe_decimal(value)
    return format(normalized, "f").rstrip("0").rstrip(".") or "0"


def _normalized_text(value) -> str:
    return str(value or "").strip().lower()


def _translate_report_label(value, lang_code: str | None = None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    language = (lang_code or get_language() or "az").lower()
    with override(language):
        translated = _T(text)
    language_base = language.split("-")[0]
    if translated == text:
        return (
            FARM_PRODUCT_NAME_TRANSLATIONS.get(language_base, {}).get(text)
            or GENERIC_OPTION_TRANSLATIONS.get(language_base, {}).get(text)
            or translated
        )
    return translated


def _parse_date_param(raw_value: str | None, fallback: date) -> date:
    raw = str(raw_value or "").strip()
    if not raw:
        return fallback
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return fallback


def _normalize_date_range(raw_from: str | None, raw_to: str | None) -> tuple[date, date]:
    today = timezone.localdate()
    default_from = today.replace(month=1, day=1)
    date_to = _parse_date_param(raw_to, today)
    date_from = _parse_date_param(raw_from, default_from)
    if date_from > date_to:
        date_from, date_to = date_to, date_from
    return date_from, date_to


def _normalize_purpose(raw_value: str | None) -> str:
    value = str(raw_value or "tax").strip().lower()
    return value if value in REPORT_PURPOSES else "tax"


def _normalize_group_by(raw_value: str | None) -> str:
    value = str(raw_value or "auto").strip().lower()
    return value if value in GROUP_BY_OPTIONS else "auto"


def _report_context_cache_key(request) -> str:
    user = request.user
    language_code = (get_language() or "az").split("-")[0].lower()
    bust_value = get_reports_bust_value(user.pk)
    today_key = timezone.localdate().isoformat()
    normalized_query = urlencode(sorted(request.GET.lists()), doseq=True)
    query_hash = hashlib.md5(normalized_query.encode("utf-8")).hexdigest()
    return f"reports:context:v3:{user.pk}:{bust_value}:{language_code}:{today_key}:{query_hash}"


def _get_cached_report_context(request):
    cache_key = _report_context_cache_key(request)
    cached_context = cache.get(cache_key)
    if cached_context is not None:
        return cached_context
    context = _report_context(request)
    cache.set(cache_key, context, REPORT_CONTEXT_CACHE_TTL)
    return context


def _resolved_group_by(date_from: date, date_to: date, selected: str) -> str:
    if selected != "auto":
        return selected
    total_days = (date_to - date_from).days + 1
    if total_days <= 45:
        return "day"
    if total_days <= 210:
        return "week"
    return "month"


def _bucket_start(day: date, group_by: str) -> date:
    if group_by == "week":
        return day - timedelta(days=day.weekday())
    if group_by == "month":
        return day.replace(day=1)
    return day


def _advance_bucket(day: date, group_by: str) -> date:
    if group_by == "day":
        return day + timedelta(days=1)
    if group_by == "week":
        return day + timedelta(days=7)
    if day.month == 12:
        return date(day.year + 1, 1, 1)
    return date(day.year, day.month + 1, 1)


def _full_day_label(day: date, *, include_year: bool = False) -> str:
    label = f"{day.day} {AZ_MONTH_NAMES.get(day.month, day.strftime('%B'))}"
    if include_year:
        return f"{label} {day.year}"
    return label


def _bucket_label(day: date, group_by: str) -> str:
    if group_by == "day":
        return _full_day_label(day)
    if group_by == "week":
        end_day = day + timedelta(days=6)
        return f"{_full_day_label(day)} - {_full_day_label(end_day)}"
    return f"{AZ_MONTH_NAMES.get(day.month, day.strftime('%B'))} {day.year}"


def _bucket_iso(day: date, group_by: str) -> str:
    if group_by == "month":
        return day.strftime("%Y-%m")
    return day.isoformat()


def _iter_buckets(date_from: date, date_to: date, group_by: str):
    current = _bucket_start(date_from, group_by)
    last = _bucket_start(date_to, group_by)
    while current <= last:
        yield current
        current = _advance_bucket(current, group_by)

def _build_expense_subcategory_lookup() -> dict[str, ExpenseSubCategory]:
    lookup: dict[str, ExpenseSubCategory] = {}
    for subcategory in ExpenseSubCategory.objects.select_related("category").all():
        name = _normalized_text(subcategory.name)
        if name:
            lookup[name] = subcategory
    return lookup


def _expense_category_name(expense: Expense, subcat_lookup: dict[str, ExpenseSubCategory], lang_code: str | None = None) -> str:
    category_name = getattr(getattr(expense.subcategory, "category", None), "name", None)
    if category_name:
        return _translate_report_label(category_name, lang_code)

    def resolve_subcategory(name: str | None):
        return subcat_lookup.get(_normalized_text(name))

    match = resolve_subcategory(expense.manual_name) or resolve_subcategory(expense.title)
    if not match and expense.title:
        title_lower = _normalized_text(expense.title)
        heuristic_map = {
            "toxum alışı": "toxumlar",
            "heyvan alışı": "heyvan alışı",
            "alət alışı": "texnika alışı",
            "texnika alışı": "texnika alışı",
        }
        for prefix, lookup_key in heuristic_map.items():
            if title_lower.startswith(prefix):
                match = resolve_subcategory(lookup_key)
                if match:
                    break

    if match and match.category:
        return _translate_report_label(match.category.name, lang_code)

    if expense.manual_name:
        return _translate_report_label(expense.manual_name, lang_code)
    return _translate_report_label(_("Digər"), lang_code)


def _expense_line_name(expense: Expense, lang_code: str | None = None) -> str:
    title = str(expense.title or "").strip()
    if title:
        return _translate_report_label(translate_expense_title(title), lang_code)
    if expense.manual_name:
        return _translate_report_label(translate_expense_title(str(expense.manual_name).strip()), lang_code)
    if expense.subcategory:
        return _translate_report_label(expense.subcategory.name, lang_code)
    return _translate_report_label(_("Xərc"), lang_code)


def _profit_tone(value: Decimal) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "neutral"


def _is_primary_agri_sale(income: Income) -> bool:
    category = _normalized_text(income.category)
    item_name = _normalized_text(income.item_name)
    content_model = _normalized_text(getattr(getattr(income, "content_type", None), "model", None))

    if content_model == "tool":
        return False

    if content_model in {"animal", "seed"}:
        return True

    if any(keyword in category for keyword in RAW_AGRI_CATEGORY_KEYWORDS):
        return True

    if "süd" in item_name and not any(keyword in item_name for keyword in PROCESSED_PRODUCT_KEYWORDS):
        return True

    if "yumurta" in item_name:
        return True

    if item_name == "bal":
        return True

    if any(keyword in item_name for keyword in PROCESSED_PRODUCT_KEYWORDS):
        return False

    if category in {"digər", "xüsusi gəlir"}:
        return False

    return False


def _estimated_income_tax(income: Income) -> dict:
    gross_amount = _quantize_money(income.amount)
    reference_vat = _quantize_money(gross_amount * AZ_STANDARD_VAT_RATE)
    if _is_primary_agri_sale(income) and AGRI_TAX_EXEMPTION_START <= income.date < AGRI_TAX_EXEMPTION_END:
        return {
            "rate": Decimal("0.00"),
            "rate_percent": Decimal("0.00"),
            "due": Decimal("0.00"),
            "reference_vat": reference_vat,
            "rule": str(_("Aqrar güzəşt")),
            "note": str(
                _(
                    "İlkin formada təqdim edilən kənd təsərrüfatı məhsulu və ya diri heyvan satışı 1 Yanvar 2027-dək vergidən azaddır."
                )
            ),
        }

    return {
        "rate": AZ_STANDARD_VAT_RATE,
        "rate_percent": AZ_STANDARD_VAT_RATE_PERCENT,
        "due": reference_vat,
        "reference_vat": reference_vat,
        "rule": str(_("Standart ƏDV arayışı")),
        "note": str(
            _("Bu satış ilkin kənd təsərrüfatı məhsulu sayılmadığı üçün standart ƏDV arayışı tətbiq edilib.")
        ),
    }


def _report_font_name() -> str:
    if not REPORTLAB_AVAILABLE:
        return "Helvetica"

    font_name = "FarmReportFont"
    try:
        pdfmetrics.getFont(font_name)
        return font_name
    except Exception:
        pass

    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            pdfmetrics.registerFont(TTFont(font_name, path))
            return font_name
        except Exception:
            continue
    return "Helvetica"


@lru_cache(maxsize=None)
def _report_image_font(size: int, bold: bool = False):
    if not PILLOW_AVAILABLE:
        return None

    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if not path or not os.path.exists(path):
            continue
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _build_pillow_pdf(context) -> bytes:
    if not PILLOW_AVAILABLE:
        raise RuntimeError("Pillow PDF renderer is unavailable.")

    page_width = 1240
    page_height = 1754
    margin = 64
    panel_radius = 28
    colors_map = {
        "page": "#f3f7f4",
        "panel": "#ffffff",
        "panel_muted": "#f7faf8",
        "border": "#d6e2dc",
        "text": "#163126",
        "muted": "#61766d",
        "hero": "#174c3f",
        "hero_alt": "#2d7a67",
        "income": "#1d8a4d",
        "expense": "#e17f3e",
        "net": "#2563eb",
        "danger": "#c2410c",
        "tax": "#f4c542",
        "line": "#dde7e2",
        "chip": "#e8f3ef",
    }
    title_font = _report_image_font(48, True)
    heading_font = _report_image_font(30, True)
    subheading_font = _report_image_font(22, True)
    body_font = _report_image_font(20)
    body_bold_font = _report_image_font(20, True)
    small_font = _report_image_font(16)
    small_bold_font = _report_image_font(16, True)

    def new_page():
        page = Image.new("RGBA", (page_width, page_height), colors_map["page"])
        draw = ImageDraw.Draw(page)
        return page, draw

    def text_size(draw, text, font):
        bbox = draw.textbbox((0, 0), str(text or ""), font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    def line_height(draw, font):
        return text_size(draw, "Ag", font)[1]

    def wrap_text(draw, text, font, max_width, max_lines=None):
        raw = str(text or "").strip()
        if not raw:
            return []
        lines = []
        for paragraph in raw.splitlines():
            words = paragraph.split()
            if not words:
                lines.append("")
                continue
            current = words[0]
            for word in words[1:]:
                trial = f"{current} {word}"
                if text_size(draw, trial, font)[0] <= max_width:
                    current = trial
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
        if max_lines and len(lines) > max_lines:
            lines = lines[:max_lines]
            while lines and text_size(draw, f"{lines[-1]}…", font)[0] > max_width and len(lines[-1]) > 1:
                lines[-1] = lines[-1][:-1]
            if lines:
                lines[-1] = f"{lines[-1]}…"
        return lines

    def draw_wrapped_text(draw, text, x, y, font, fill, max_width, *, max_lines=None, gap=8):
        lines = wrap_text(draw, text, font, max_width, max_lines=max_lines)
        if not lines:
            return y
        step = line_height(draw, font) + gap
        for line in lines:
            draw.text((x, y), line, font=font, fill=fill)
            y += step
        return y - gap

    def panel(draw, box, fill, outline=None, radius=panel_radius):
        draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline or colors_map["border"], width=2)

    def pill(draw, box, fill, text, text_fill):
        draw.rounded_rectangle(box, radius=999, fill=fill)
        tw, th = text_size(draw, text, small_bold_font)
        draw.text((box[0] + 14, box[1] + ((box[3] - box[1] - th) / 2) - 1), text, font=small_bold_font, fill=text_fill)

    def money(value):
        return f"{value} AZN"

    def shorten(text, limit=28):
        text = str(text or "")
        return text if len(text) <= limit else f"{text[:limit - 1]}…"

    def draw_kpi_card(draw, box, label, value, note, accent_fill):
        panel(draw, box, "#ffffff", accent_fill)
        draw.rounded_rectangle((box[0] + 18, box[1] + 18, box[0] + 34, box[1] + 34), radius=8, fill=accent_fill)
        draw.text((box[0] + 48, box[1] + 16), label, font=small_bold_font, fill=colors_map["muted"])
        draw.text((box[0] + 18, box[1] + 58), value, font=subheading_font, fill=colors_map["text"])
        draw_wrapped_text(draw, note, box[0] + 18, box[1] + 102, small_font, colors_map["muted"], box[2] - box[0] - 36, max_lines=2, gap=4)

    def draw_simple_table(draw, box, title, headers, rows, widths, *, empty_label):
        panel(draw, box, colors_map["panel"], colors_map["border"])
        x = box[0] + 24
        y = box[1] + 22
        draw.text((x, y), title, font=heading_font, fill=colors_map["text"])
        y += 52
        header_box = (x, y, box[2] - 24, y + 48)
        draw.rounded_rectangle(header_box, radius=16, fill=colors_map["panel_muted"])
        inner_width = header_box[2] - header_box[0] - 20
        total_ratio = sum(widths)
        column_widths = [int((inner_width * value) / total_ratio) for value in widths]
        column_widths[-1] += inner_width - sum(column_widths)
        cursor = header_box[0] + 10
        for index, header in enumerate(headers):
            draw.text((cursor, header_box[1] + 13), header, font=small_bold_font, fill=colors_map["muted"])
            cursor += column_widths[index]
        y = header_box[3] + 10
        if not rows:
            draw.text((x, y + 18), empty_label, font=body_font, fill=colors_map["muted"])
            return
        for index, row in enumerate(rows):
            row_box = (x, y, box[2] - 24, y + 74)
            draw.rounded_rectangle(
                row_box,
                radius=18,
                fill="#ffffff" if index % 2 == 0 else "#f9fbfa",
                outline=colors_map["line"],
                width=1,
            )
            cursor = row_box[0] + 10
            for col_index, value in enumerate(row):
                cell_width = column_widths[col_index] - 10
                lines = wrap_text(draw, value, body_font, max(cell_width, 20), max_lines=2)
                top = row_box[1] + 12
                for line in lines or [""]:
                    draw.text((cursor, top), line, font=body_font, fill=colors_map["text"])
                    top += line_height(draw, body_font) + 2
                cursor += column_widths[col_index]
            y += 82

    pages = []

    page, draw = new_page()
    hero_box = (margin, margin, page_width - margin, 392)
    panel(draw, hero_box, colors_map["hero"], colors_map["hero"], radius=40)
    draw.ellipse((hero_box[2] - 300, hero_box[1] - 40, hero_box[2] - 40, hero_box[1] + 220), fill=(255, 255, 255, 28))
    draw.ellipse((hero_box[2] - 420, hero_box[1] + 80, hero_box[2] - 180, hero_box[1] + 320), fill=(72, 169, 140, 120))
    draw.text((hero_box[0] + 34, hero_box[1] + 32), str(_("Ferma hesabatı")), font=small_bold_font, fill="#d6efe5")
    draw.text((hero_box[0] + 34, hero_box[1] + 72), context["purpose_meta"]["label"], font=title_font, fill="#ffffff")
    draw_wrapped_text(
        draw,
        context["purpose_meta"]["description"],
        hero_box[0] + 34,
        hero_box[1] + 142,
        body_font,
        "#e7f5ef",
        560,
        max_lines=2,
        gap=6,
    )
    pill(draw, (hero_box[0] + 34, hero_box[1] + 226, hero_box[0] + 380, hero_box[1] + 270), "#edf8f3", context["range_label"], colors_map["hero"])
    pill(
        draw,
        (hero_box[0] + 34, hero_box[1] + 284, hero_box[0] + 260, hero_box[1] + 328),
        "#1e6451",
        f"{str(_('Qruplaşdırma'))}: {context['filters']['resolved_group_by_label']}",
        "#ffffff",
    )

    metric_x = hero_box[2] - 332
    metric_y = hero_box[1] + 36
    for label, value in (
        (str(_("Aktiv gün")), str(context["kpis"]["active_days"])),
        (str(_("Müsbət period")), str(context["kpis"]["profitable_periods"])),
        (str(_("Ən yaxşı period")), shorten(context["kpis"]["best_net_label"], 22)),
    ):
        metric_box = (metric_x, metric_y, hero_box[2] - 34, metric_y + 84)
        draw.rounded_rectangle(metric_box, radius=22, fill=(255, 255, 255, 36), outline=(255, 255, 255, 44), width=1)
        draw.text((metric_box[0] + 18, metric_box[1] + 14), label, font=small_bold_font, fill="#d8efe7")
        draw.text((metric_box[0] + 18, metric_box[1] + 40), value, font=body_bold_font, fill="#ffffff")
        metric_y += 96

    card_top = 432
    card_gap = 20
    card_width = int((page_width - (margin * 2) - (card_gap * 3)) / 4)
    card_note_map = (
        (str(_("Ümumi gəlir")), money(context["kpis"]["total_income_display"]), str(_("Bütün satışların cəmi")), "#dff5e7"),
        (str(_("Ümumi xərc")), money(context["kpis"]["total_expense_display"]), str(_("Bütün xərclərin cəmi")), "#fbe7db"),
        (str(_("Xalis qazanc")), money(context["kpis"]["net_profit_display"]), str(_("Gəlir və xərc fərqi")), "#dfe9fb"),
        (str(_("Hesablanan vergi")), money(context["tax"]["total_due_display"]), str(_("Satışlara uyğun hesablanır")), "#f9efc7"),
    )
    for index, (label, value, note, accent_fill) in enumerate(card_note_map):
        left = margin + (card_width + card_gap) * index
        draw_kpi_card(draw, (left, card_top, left + card_width, card_top + 190), label, value, note, accent_fill)

    tax_y = 654
    tax_box_height = 152
    tax_columns = 2
    tax_gap = 18
    tax_width = int((page_width - (margin * 2) - tax_gap) / tax_columns)
    tax_cards = [
        (str(_("Standart ƏDV arayışı")), f"{context['tax']['reference_rate_display']}%", str(_("Müqayisə üçün dərəcə"))),
        (str(_("Güzəşt olmasaydı ƏDV")), money(context["tax"]["reference_vat_amount_display"]), str(_("Arayış məbləği"))),
        (str(_("Vergi qaydası")), context["tax"]["agri_rule_label"], context["tax"]["agri_rule_period"]),
        (str(_("Torpaq vergisi")), str(_("Ayrı hesablanır")), context["tax"]["land_tax_note"]),
    ]
    for index, (label, value, note) in enumerate(tax_cards):
        row = index // 2
        col = index % 2
        left = margin + (tax_width + tax_gap) * col
        top = tax_y + (tax_box_height + tax_gap) * row
        panel(draw, (left, top, left + tax_width, top + tax_box_height), "#fffdf5", "#efe0a8")
        draw.text((left + 22, top + 20), label, font=small_bold_font, fill=colors_map["muted"])
        draw.text((left + 22, top + 56), value, font=subheading_font, fill=colors_map["text"])
        draw_wrapped_text(draw, note, left + 22, top + 102, small_font, colors_map["muted"], tax_width - 44, max_lines=2, gap=3)

    note_box = (margin, 994, page_width - margin, 1174)
    panel(draw, note_box, "#f7faf8", colors_map["border"])
    draw.text((note_box[0] + 24, note_box[1] + 18), str(_("Vergi qeydi")), font=body_bold_font, fill=colors_map["text"])
    draw_wrapped_text(draw, context["tax"]["agri_rule_note"], note_box[0] + 24, note_box[1] + 56, body_font, colors_map["muted"], note_box[2] - note_box[0] - 48, max_lines=3, gap=4)
    draw_wrapped_text(draw, context["tax"]["source_note"], note_box[0] + 24, note_box[1] + 116, small_font, colors_map["muted"], note_box[2] - note_box[0] - 48, max_lines=2, gap=3)

    insights_box = (margin, 1210, page_width - margin, 1642)
    panel(draw, insights_box, colors_map["panel"], colors_map["border"])
    draw.text((insights_box[0] + 24, insights_box[1] + 18), str(_("Hesabat xülasəsi")), font=heading_font, fill=colors_map["text"])
    insight_y = insights_box[1] + 82
    for insight in context["purpose_insights"]:
        draw.rounded_rectangle((insights_box[0] + 24, insight_y, insights_box[0] + 48, insight_y + 24), radius=12, fill=colors_map["chip"])
        draw.text((insights_box[0] + 31, insight_y - 1), "✓", font=body_bold_font, fill=colors_map["income"])
        draw_wrapped_text(draw, insight, insights_box[0] + 64, insight_y - 4, body_font, colors_map["text"], insights_box[2] - insights_box[0] - 96, max_lines=2, gap=4)
        insight_y += 84
    snapshot_box = (insights_box[0] + 24, 1486, insights_box[2] - 24, insights_box[3] - 24)
    draw.rounded_rectangle(snapshot_box, radius=22, fill="#f8fbfa", outline=colors_map["line"], width=1)
    snapshot_items = [
        (str(_("Orta gəlir")), money(context["kpis"]["average_income_display"])),
        (str(_("Orta xərc")), money(context["kpis"]["average_expense_display"])),
        (str(_("Ödəniş gücü")), f"{context['kpis']['coverage_ratio_display']}x" if context["kpis"]["coverage_ratio_display"] else "—"),
        (str(_("Vergi qənaəti")), money(context["tax"]["savings_amount_display"])),
    ]
    snap_x = snapshot_box[0] + 22
    for label, value in snapshot_items:
        draw.text((snap_x, snapshot_box[1] + 18), label, font=small_bold_font, fill=colors_map["muted"])
        draw.text((snap_x, snapshot_box[1] + 52), value, font=body_bold_font, fill=colors_map["text"])
        snap_x += 266
    pages.append(page)

    page, draw = new_page()
    left_box = (margin, margin, 800, 874)
    product_rows = [
        [
            row["item_name"],
            row["category"],
            f"{_plain_number(row['quantity'])} {row['unit']}".strip(),
            money(row["amount_display"]),
            money(row["tax_due_display"]),
        ]
        for row in context["product_rows"][:8]
    ]
    draw_simple_table(
        draw,
        left_box,
        str(_("Məhsul növlərinə görə müqayisə")),
        [str(_("Məhsul")), str(_("Kateqoriya")), str(_("Miqdar")), str(_("Gəlir")), str(_("Vergi"))],
        product_rows,
        [2.0, 1.5, 1.2, 1.2, 1.2],
        empty_label=str(_("Bu tarix aralığında satış məlumatı yoxdur.")),
    )

    right_box = (832, margin, page_width - margin, 874)
    panel(draw, right_box, colors_map["panel"], colors_map["border"])
    draw.text((right_box[0] + 24, right_box[1] + 22), str(_("Əsas xərc istiqamətləri")), font=heading_font, fill=colors_map["text"])
    breakdown_y = right_box[1] + 88
    if context["expense_breakdown"]:
        for row in context["expense_breakdown"][:8]:
            row_box = (right_box[0] + 22, breakdown_y, right_box[2] - 22, breakdown_y + 78)
            draw.rounded_rectangle(row_box, radius=20, fill="#f9fbfa", outline=colors_map["line"], width=1)
            draw.text((row_box[0] + 16, row_box[1] + 14), row["name"], font=body_bold_font, fill=colors_map["text"])
            draw.text((row_box[2] - 180, row_box[1] + 14), money(row["amount_display"]), font=body_bold_font, fill=colors_map["danger"])
            bar_box = (row_box[0] + 16, row_box[1] + 46, row_box[2] - 16, row_box[1] + 58)
            draw.rounded_rectangle(bar_box, radius=999, fill="#e4ece8")
            fill_width = int(((bar_box[2] - bar_box[0]) * row["share_pct"]) / 100)
            draw.rounded_rectangle((bar_box[0], bar_box[1], bar_box[0] + max(fill_width, 8), bar_box[3]), radius=999, fill=colors_map["expense"])
            draw.text((row_box[0] + 16, row_box[1] + 60), f"{row['share_pct']}%", font=small_bold_font, fill=colors_map["muted"])
            breakdown_y += 92
    else:
        draw.text((right_box[0] + 24, breakdown_y), str(_("Bu tarix aralığında xərc məlumatı yoxdur.")), font=body_font, fill=colors_map["muted"])

    timeline_box = (margin, 922, page_width - margin, page_height - margin - 54)
    panel(draw, timeline_box, colors_map["panel"], colors_map["border"])
    draw.text((timeline_box[0] + 24, timeline_box[1] + 22), str(_("Period müqayisəsi")), font=heading_font, fill=colors_map["text"])
    draw.text((timeline_box[0] + 24, timeline_box[1] + 62), str(_("Gəlir, xərc və xalis qazanc ən son periodlar üzrə")), font=body_font, fill=colors_map["muted"])
    timeline_points = context["chart"]["points"][-8:] or [context["chart"]["initial_point"]]
    max_metric = max(
        max(abs(point["income"]), abs(point["expense"]), abs(point["net"])) for point in timeline_points
    ) or 1
    row_y = timeline_box[1] + 118
    for point in timeline_points:
        row_box = (timeline_box[0] + 24, row_y, timeline_box[2] - 24, row_y + 96)
        draw.rounded_rectangle(row_box, radius=18, fill="#fbfcfb", outline=colors_map["line"], width=1)
        draw.text((row_box[0] + 16, row_box[1] + 14), shorten(point["label"], 36), font=body_bold_font, fill=colors_map["text"])
        draw.text((row_box[2] - 210, row_box[1] + 14), money(point["net_display"]), font=body_bold_font, fill=colors_map["net"] if point["net"] >= 0 else colors_map["danger"])
        bars = [
            (str(_("Gəlir")), point["income"], colors_map["income"]),
            (str(_("Xərc")), point["expense"], colors_map["expense"]),
            (str(_("Xalis")), abs(point["net"]), colors_map["net"] if point["net"] >= 0 else colors_map["danger"]),
        ]
        bar_y = row_box[1] + 48
        for label, value, fill in bars:
            draw.text((row_box[0] + 16, bar_y - 6), label, font=small_bold_font, fill=colors_map["muted"])
            track = (row_box[0] + 94, bar_y, row_box[2] - 16, bar_y + 10)
            draw.rounded_rectangle(track, radius=999, fill="#e5ece8")
            fill_width = int(((track[2] - track[0]) * float(value)) / float(max_metric))
            draw.rounded_rectangle((track[0], track[1], track[0] + max(fill_width, 6), track[3]), radius=999, fill=fill)
            bar_y += 22
        row_y += 108
    pages.append(page)

    transaction_rows = context["all_transactions"]
    chunk_size = 18
    transaction_chunks = [transaction_rows[index:index + chunk_size] for index in range(0, len(transaction_rows), chunk_size)] or [[]]
    for chunk_index, chunk in enumerate(transaction_chunks, start=1):
        page, draw = new_page()
        panel(draw, (margin, margin, page_width - margin, page_height - margin - 54), colors_map["panel"], colors_map["border"])
        draw.text((margin + 24, margin + 22), str(_("Əməliyyat jurnalı")), font=heading_font, fill=colors_map["text"])
        draw.text((margin + 24, margin + 62), f"{str(_('Səhifə'))} {chunk_index}", font=body_font, fill=colors_map["muted"])
        table_rows = []
        for row in chunk:
            amount_display = money(row["amount_display"])
            if row["type"] == "income":
                amount_display = f"+ {amount_display}"
            else:
                amount_display = f"- {amount_display}"
            tax_display = money(row["tax_due_display"]) if row["type"] == "income" else "—"
            table_rows.append(
                [
                    row["date"].strftime("%d.%m.%Y"),
                    row["type_label"],
                    row["line_name"],
                    row["group_name"],
                    amount_display,
                    tax_display,
                ]
            )
        draw_simple_table(
            draw,
            (margin + 18, margin + 94, page_width - margin - 18, page_height - margin - 78),
            str(_("Əməliyyat siyahısı")),
            [str(_("Tarix")), str(_("Növ")), str(_("Ad")), str(_("Kateqoriya")), str(_("Məbləğ")), str(_("Vergi"))],
            table_rows,
            [1.1, 0.9, 2.0, 1.5, 1.1, 1.0],
            empty_label=str(_("Bu tarix aralığında heç bir əməliyyat tapılmadı.")),
        )
        pages.append(page)

    total_pages = len(pages)
    for index, page in enumerate(pages, start=1):
        draw = ImageDraw.Draw(page)
        footer_text = f"{str(_('Hazırlanma tarixi'))}: {timezone.localdate().strftime('%d.%m.%Y')}   •   {str(_('Səhifə'))} {index}/{total_pages}"
        draw.text((margin, page_height - margin + 4), footer_text, font=small_font, fill=colors_map["muted"])

    rgb_pages = [page.convert("RGB") for page in pages]
    buffer = BytesIO()
    rgb_pages[0].save(
        buffer,
        format="PDF",
        save_all=True,
        append_images=rgb_pages[1:],
        resolution=150.0,
    )
    return buffer.getvalue()


def _build_preset_query(date_from: date, date_to: date, purpose: str, group_by: str) -> str:
    return urlencode(
        {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "purpose": purpose,
            "group_by": group_by,
        }
    )


def _report_context(request):
    user = request.user
    lang_code = (get_language() or "az").lower()
    today = timezone.localdate()
    date_from, date_to = _normalize_date_range(
        request.GET.get("date_from"),
        request.GET.get("date_to"),
    )
    selected_purpose = _normalize_purpose(request.GET.get("purpose"))
    selected_group_by = _normalize_group_by(request.GET.get("group_by"))
    resolved_group_by = _resolved_group_by(date_from, date_to, selected_group_by)

    incomes = list(
        Income.objects.filter(created_by=user, date__range=(date_from, date_to))
        .select_related("content_type")
        .order_by("-date", "-id")
    )
    expenses = list(
        Expense.objects.filter(created_by=user, date__range=(date_from, date_to))
        .select_related("subcategory", "subcategory__category")
        .order_by("-date", "-id")
    )
    expense_subcat_lookup = _build_expense_subcategory_lookup()

    income_tax_map = {income.id: _estimated_income_tax(income) for income in incomes}

    total_income = sum((_safe_decimal(item.amount) for item in incomes), start=Decimal("0"))
    total_expense = sum((_safe_decimal(item.amount) for item in expenses), start=Decimal("0"))
    net_profit = total_income - total_expense
    total_tax_due = sum((detail["due"] for detail in income_tax_map.values()), start=Decimal("0"))
    total_reference_vat = sum((detail["reference_vat"] for detail in income_tax_map.values()), start=Decimal("0"))
    tax_savings = total_reference_vat - total_tax_due

    income_days = {item.date for item in incomes}
    expense_days = {item.date for item in expenses}
    all_active_days = sorted(income_days | expense_days)

    timeline_map = {
        bucket: {
            "label": _bucket_label(bucket, resolved_group_by),
            "date_iso": _bucket_iso(bucket, resolved_group_by),
            "income": Decimal("0"),
            "expense": Decimal("0"),
            "tax": Decimal("0"),
        }
        for bucket in _iter_buckets(date_from, date_to, resolved_group_by)
    }

    for income in incomes:
        tax_detail = income_tax_map[income.id]
        bucket = _bucket_start(income.date, resolved_group_by)
        timeline_map.setdefault(
            bucket,
            {
                "label": _bucket_label(bucket, resolved_group_by),
                "date_iso": _bucket_iso(bucket, resolved_group_by),
                "income": Decimal("0"),
                "expense": Decimal("0"),
                "tax": Decimal("0"),
            },
        )
        timeline_map[bucket]["income"] += _safe_decimal(income.amount)
        timeline_map[bucket]["tax"] += tax_detail["due"]

    for expense in expenses:
        bucket = _bucket_start(expense.date, resolved_group_by)
        timeline_map.setdefault(
            bucket,
            {
                "label": _bucket_label(bucket, resolved_group_by),
                "date_iso": _bucket_iso(bucket, resolved_group_by),
                "income": Decimal("0"),
                "expense": Decimal("0"),
                "tax": Decimal("0"),
            },
        )
        timeline_map[bucket]["expense"] += _safe_decimal(expense.amount)

    timeline_points = []
    profitable_periods = 0
    best_net_point = None
    for bucket in sorted(timeline_map.keys()):
        income_value = timeline_map[bucket]["income"]
        expense_value = timeline_map[bucket]["expense"]
        tax_value = timeline_map[bucket]["tax"]
        net_value = income_value - expense_value
        if net_value > 0:
            profitable_periods += 1
        point = {
            "label": timeline_map[bucket]["label"],
            "date_iso": timeline_map[bucket]["date_iso"],
            "income": float(income_value),
            "expense": float(expense_value),
            "net": float(net_value),
            "tax": float(tax_value),
            "income_display": format_currency(income_value, 2),
            "expense_display": format_currency(expense_value, 2),
            "net_display": format_currency(net_value, 2),
            "tax_display": format_currency(tax_value, 2),
            "tone": _profit_tone(net_value),
        }
        if best_net_point is None or net_value > _safe_decimal(best_net_point["net"]):
            best_net_point = point
        timeline_points.append(point)

    initial_point = (
        timeline_points[-1]
        if timeline_points
        else {
            "label": f"{_full_day_label(date_from)} - {_full_day_label(date_to)}",
            "income": 0,
            "expense": 0,
            "net": 0,
            "tax": 0,
            "income_display": format_currency(0, 2),
            "expense_display": format_currency(0, 2),
            "net_display": format_currency(0, 2),
            "tax_display": format_currency(0, 2),
            "tone": "neutral",
        }
    )

    average_income = Decimal("0")
    average_expense = Decimal("0")
    if timeline_points:
        average_income = total_income / Decimal(len(timeline_points))
        average_expense = total_expense / Decimal(len(timeline_points))

    coverage_ratio = None
    if total_expense > 0:
        coverage_ratio = total_income / total_expense

    product_map = defaultdict(
        lambda: {
            "category": "",
            "item_name": "",
            "unit": "",
            "quantity": Decimal("0"),
            "amount": Decimal("0"),
            "tax_due": Decimal("0"),
        }
    )
    for income in incomes:
        tax_detail = income_tax_map[income.id]
        key = (
            str(income.category or "").strip(),
            str(income.item_name or "").strip(),
            str(income.unit or "").strip(),
        )
        row = product_map[key]
        row["category"] = _translate_report_label(str(income.category or _("Digər")).strip(), lang_code)
        row["item_name"] = _translate_report_label(str(income.item_name or _("Məhsul")).strip(), lang_code)
        row["unit"] = str(income.unit or "").strip()
        row["quantity"] += _safe_decimal(income.quantity)
        row["amount"] += _safe_decimal(income.amount)
        row["tax_due"] += tax_detail["due"]

    product_rows = sorted(product_map.values(), key=lambda item: item["amount"], reverse=True)
    for row in product_rows:
        pct = 0
        if total_income > 0:
            pct = round((float(row["amount"]) / float(total_income)) * 100)
        row["share_pct"] = pct
        row["amount_display"] = format_currency(row["amount"], 2)
        row["tax_due_display"] = format_currency(row["tax_due"], 2)
        row["avg_price_display"] = format_currency(
            row["amount"] / row["quantity"] if row["quantity"] else 0,
            2,
        )

    expense_map = defaultdict(Decimal)
    for expense in expenses:
        expense_map[_expense_category_name(expense, expense_subcat_lookup, lang_code)] += _safe_decimal(expense.amount)

    expense_breakdown = []
    for category_name, amount in sorted(expense_map.items(), key=lambda item: item[1], reverse=True):
        pct = 0
        if total_expense > 0:
            pct = round((float(amount) / float(total_expense)) * 100)
        expense_breakdown.append(
            {
                "name": category_name,
                "amount": amount,
                "amount_display": format_currency(amount, 2),
                "share_pct": pct,
            }
        )

    transactions = []
    for income in incomes:
        tax_detail = income_tax_map[income.id]
        transactions.append(
            {
                "date": income.date,
                "type": "income",
                "type_label": _("Gəlir"),
                "line_name": _translate_report_label(str(income.item_name or _("Satış")).strip(), lang_code),
                "group_name": _translate_report_label(str(income.category or _("Digər")).strip(), lang_code),
                "quantity": _safe_decimal(income.quantity),
                "unit": str(income.unit or "").strip(),
                "amount": _safe_decimal(income.amount),
                "amount_display": format_currency(income.amount, 2),
                "tax_due": tax_detail["due"],
                "tax_due_display": format_currency(tax_detail["due"], 2),
                "tax_rate_percent": tax_detail["rate_percent"],
                "tax_rate_display": format_currency(tax_detail["rate_percent"], 2),
                "tax_rule": tax_detail["rule"],
                "note": str(income.additional_info or "").strip(),
            }
        )
    for expense in expenses:
        transactions.append(
            {
                "date": expense.date,
                "type": "expense",
                "type_label": str(_("Xərc")),
                "line_name": _expense_line_name(expense, lang_code),
                "group_name": _expense_category_name(expense, expense_subcat_lookup, lang_code),
                "quantity": None,
                "unit": "",
                "amount": _safe_decimal(expense.amount),
                "amount_display": format_currency(expense.amount, 2),
                "tax_due": Decimal("0.00"),
                "tax_due_display": format_currency(0, 2),
                "tax_rate_percent": Decimal("0.00"),
                "tax_rate_display": format_currency(0, 2),
                "tax_rule": str(_("Yoxdur")),
                "note": str(expense.additional_info or "").strip(),
            }
        )
    transactions.sort(key=lambda item: (item["date"], item["amount"]), reverse=True)

    tax_context = {
        "total_due": total_tax_due,
        "total_due_display": format_currency(total_tax_due, 2),
        "reference_rate_percent": AZ_STANDARD_VAT_RATE_PERCENT,
        "reference_rate_display": format_currency(AZ_STANDARD_VAT_RATE_PERCENT, 2),
        "reference_vat_amount": total_reference_vat,
        "reference_vat_amount_display": format_currency(total_reference_vat, 2),
        "savings_amount": tax_savings,
        "savings_amount_display": format_currency(tax_savings, 2),
        "agri_rule_label": _("Kənd təsərrüfatı satış güzəşti"),
        "agri_rule_period": _("1 Yanvar 2014 - 1 Yanvar 2027"),
        "agri_rule_note": _(
            "İlkin formada olan kənd təsərrüfatı satışları üçün 0 vergi, digər satışlar üçün standart ƏDV arayışı hesablanır."
        ),
        "land_tax_note": _("Torpaq vergisi və ƏDV qeydiyyatı həddi bu hesabatda ayrıca hesablanmır."),
        "source_note": _(
            "Dövlət Vergi Xidmətinin sual-cavab izahı və güzəşt məlumatları əsasında hazırlanmış arayış hesabıdır."
        ),
    }

    purpose_meta = REPORT_PURPOSES[selected_purpose]
    purpose_insights = []
    if selected_purpose == "tax":
        purpose_insights = [
            _("Seçilmiş dövr üzrə ümumi gəlir və xərc ayrıca göstərilir."),
            _("Vergi blokunda satış üzrə ödəniləcək məbləğ və güzəşt ayrıca göstərilir."),
            _("PDF çıxarışı təqdimat və paylaşım üçün daha təmiz formatda hazırlanır."),
        ]
    else:
        purpose_insights = [
            _("Gəlirin sabitliyi və xalis qazanc kredit təqdimatı üçün önə çıxarılıb."),
            _("Tarix üzrə sütun qrafiki gəlir, xərc və xalis qazancı rahat müqayisə etməyə imkan verir."),
            _("Vergi və məhsul müqayisəsi paneli maliyyə şəklini daha aydın göstərir."),
        ]

    preset_ranges = [
        {
            "label": _("Son 30 gün"),
            "query": _build_preset_query(today - timedelta(days=29), today, selected_purpose, selected_group_by),
        },
        {
            "label": _("Son 90 gün"),
            "query": _build_preset_query(today - timedelta(days=89), today, selected_purpose, selected_group_by),
        },
        {
            "label": _("Bu il"),
            "query": _build_preset_query(today.replace(month=1, day=1), today, selected_purpose, selected_group_by),
        },
    ]

    query_string = _build_preset_query(date_from, date_to, selected_purpose, selected_group_by)

    return {
        "filters": {
            "date_from": date_from,
            "date_to": date_to,
            "selected_purpose": selected_purpose,
            "selected_group_by": selected_group_by,
            "resolved_group_by": resolved_group_by,
            "resolved_group_by_label": GROUP_BY_OPTIONS.get(resolved_group_by, GROUP_BY_OPTIONS["auto"]),
            "purpose_options": [
                {"value": value, "label": meta["label"]}
                for value, meta in REPORT_PURPOSES.items()
            ],
            "group_by_options": [
                {"value": value, "label": label}
                for value, label in GROUP_BY_OPTIONS.items()
            ],
            "preset_ranges": preset_ranges,
        },
        "purpose_meta": purpose_meta,
        "purpose_insights": purpose_insights,
        "range_label": f"{_full_day_label(date_from, include_year=True)} - {_full_day_label(date_to, include_year=True)}",
        "kpis": {
            "total_income": total_income,
            "total_income_display": format_currency(total_income, 2),
            "total_expense": total_expense,
            "total_expense_display": format_currency(total_expense, 2),
            "net_profit": net_profit,
            "net_profit_display": format_currency(net_profit, 2),
            "coverage_ratio": coverage_ratio,
            "coverage_ratio_display": format_currency(coverage_ratio, 2) if coverage_ratio is not None else None,
            "active_days": len(all_active_days),
            "profitable_periods": profitable_periods,
            "average_income_display": format_currency(average_income, 2),
            "average_expense_display": format_currency(average_expense, 2),
            "best_net_label": best_net_point["label"] if best_net_point else "—",
            "best_net_display": best_net_point["net_display"] if best_net_point else format_currency(0, 2),
            "net_tone": _profit_tone(net_profit),
        },
        "tax": tax_context,
        "chart": {
            "labels": [point["label"] for point in timeline_points],
            "points": timeline_points,
            "initial_point": initial_point,
            "series": {
                "income": [point["income"] for point in timeline_points],
                "expense": [point["expense"] for point in timeline_points],
                "net": [point["net"] for point in timeline_points],
                "tax": [point["tax"] for point in timeline_points],
            },
        },
        "product_rows": product_rows[:10],
        "expense_breakdown": expense_breakdown[:8],
        "transactions": transactions[:120],
        "all_transactions": transactions,
        "export_links": {
            "pdf": f"{reverse('reports:pdf')}?{query_string}",
        },
        "query_string": query_string,
    }


@login_required
def reports_list(request):
    context = _get_cached_report_context(request)
    return render(request, "reports/reports_list.html", context)


@login_required
def reports_form(request):
    return redirect("reports:list")


@login_required
def reports_pdf(request):
    context = _get_cached_report_context(request)
    return render(request, "reports/reports_pdf.html", context)
