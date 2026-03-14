from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, TypeVar

from django.db.models import Case, IntegerField, QuerySet, When

T = TypeVar("T")


def ensure_diger_last(items: Iterable[str]) -> List[str]:
    cleaned = [item for item in items if item]
    diger = [item for item in cleaned if item.strip().lower() == "digər"]
    rest = [item for item in cleaned if item.strip().lower() != "digər"]
    return rest + diger


def order_queryset_by_name_list(qs: QuerySet, names: Sequence[str]) -> QuerySet:
    if not names:
        return qs
    diger_index = None
    if "Digər" in names:
        diger_index = names.index("Digər")

    whens = []
    idx = 0
    for name in names:
        if name == "Digər":
            continue
        whens.append(When(name=name, then=idx))
        idx += 1

    if diger_index is not None:
        default_rank = idx
        diger_rank = idx + 1
        whens.append(When(name="Digər", then=diger_rank))
    else:
        default_rank = idx

    return qs.order_by(Case(*whens, default=default_rank, output_field=IntegerField()), "name")


def sort_objects_by_name_list(items: Iterable[T], names: Sequence[str], attr: str = "name") -> List[T]:
    if not items:
        return []
    if not names:
        return sorted(items, key=lambda obj: getattr(obj, attr, ""))
    diger_index = names.index("Digər") if "Digər" in names else None
    order_map = {name: idx for idx, name in enumerate(names) if name != "Digər"}
    diger_rank = len(order_map) + 1 if diger_index is not None else None
    default_rank = len(order_map)
    return sorted(
        items,
        key=lambda obj: (
            (
                diger_rank
                if getattr(obj, attr, "") == "Digər" and diger_rank is not None
                else order_map.get(getattr(obj, attr, ""), default_rank)
            ),
            getattr(obj, attr, ""),
        ),
    )


FARM_PRODUCT_ITEM_ORDER: Dict[str, List[str]] = {
    "Süd və Süd Məhsulları": ensure_diger_last(
        [
            "İnək südü",
            "Camış südü",
            "Keçi südü",
            "İnək pendiri",
            "Camış pendiri",
            "Keçi pendiri",
            "Qatıq",
            "Ayran",
            "Kərə yağı",
            "Qaymaq",
            "Digər",
        ]
    ),
    "Yumurta": ensure_diger_last(
        [
            "Toyuq yumurtası",
            "Hinduşka yumurtası",
            "Qaz yumurtası",
            "Ördək yumurtası",
            "Bildircin yumurtası",
            "Digər",
        ]
    ),
    "Ət Məhsulları": ensure_diger_last(
        [
            "Mal əti",
            "Dana əti",
            "Camış əti",
            "Qoyun əti",
            "Keçi əti",
            "Toyuq əti",
            "Hinduşka əti",
            "Qaz əti",
            "Ördək əti",
            "Bildircin əti",
            "Digər",
        ]
    ),
    "Meyvə": ensure_diger_last(
        [
            "Alma",
            "Armud",
            "Şaftalı",
            "Ərik",
            "Albalı",
            "Gilas",
            "Nar",
            "Üzüm",
            "Gavalı",
            "Heyva",
            "Digər",
        ]
    ),
    "Tərəvəz": ensure_diger_last(
        [
            "Pomidor",
            "Xiyar",
            "Bibər",
            "Badımcan",
            "Kahı",
            "İspanaq",
            "Soğan",
            "Sarımsaq",
            "Kartof",
            "Digər",
        ]
    ),
    "Göyərti": ensure_diger_last(
        [
            "Keşniş",
            "Şüyüt",
            "Cəfəri",
            "Yaşıl soğan",
            "Reyhan",
            "Tərxun",
            "Digər",
        ]
    ),
    "Taxıl Məhsulları": ensure_diger_last(
        [
            "Buğda",
            "Arpa",
            "Çovdar",
            "Vələmir",
            "Qarğıdalı",
            "Çəltik",
            "Digər",
        ]
    ),
    "Yem Bitkiləri": ensure_diger_last(
        [
            "Yonca",
            "Koronilla",
            "Seradella",
            "Digər",
        ]
    ),
    "Bostan Məhsulları": ensure_diger_last(
        [
            "Qarpız",
            "Yemiş",
            "Boranı",
            "Digər",
        ]
    ),
    "Bal və Arıçılıq": ensure_diger_last(
        [
            "Bal",
            "Arı mumu",
            "Arı südü",
            "Digər",
        ]
    ),
    "Gübrələr": ensure_diger_last(
        [
            "Mal peyini",
            "Qoyun peyini",
            "Keçi peyini",
            "Quş peyini",
            "Kompost",
            "Mineral gübrə",
            "Digər",
        ]
    ),
    "Digər": ["Digər"],
}

FARM_PRODUCT_CATEGORY_ORDER = ensure_diger_last(list(FARM_PRODUCT_ITEM_ORDER.keys()))

ANIMAL_SUBCATEGORY_ORDER: Dict[str, List[str]] = {
    "İribuynuzlular": ensure_diger_last(["İnək", "Dana", "Camış", "Digər"]),
    "Xırdabuynuzlular": ensure_diger_last(["Qoyun", "Keçi", "Digər"]),
    "Quşlar": ensure_diger_last(["Toyuq", "Hinduşka", "Qaz", "Ördək", "Bildircin", "Digər"]),
    "Təkdırnaqlılar": ensure_diger_last(["At", "Eşşək", "Qatır", "Digər"]),
    "Digər": ["Digər"],
}

ANIMAL_CATEGORY_ORDER = ensure_diger_last(list(ANIMAL_SUBCATEGORY_ORDER.keys()))

SEED_ITEM_ORDER: Dict[str, List[str]] = {
    "Taxıl toxumları": ensure_diger_last(
        ["Buğda toxumu", "Arpa toxumu", "Çovdar toxumu", "Vələmir toxumu", "Qarğıdalı toxumu", "Çəltik toxumu", "Digər"]
    ),
    "Paxlalı toxumları": ensure_diger_last(["Lobya toxumu", "Noxud toxumu", "Mərcimək toxumu", "Digər"]),
    "Yağlı bitki toxumları": ensure_diger_last(
        ["Günəbaxan toxumu", "Pambıq toxumu", "Soya toxumu", "Şəkər çuğunduru toxumu", "Digər"]
    ),
    "Yem bitki toxumları": ensure_diger_last(["Yonca toxumu", "Koronilla toxumu", "Seradella toxumu", "Digər"]),
    "Tərəvəz toxumları": ensure_diger_last(
        ["Pomidor toxumu", "Xiyar toxumu", "Bibər toxumu", "Badımcan toxumu", "Kahı toxumu", "İspanaq toxumu", "Digər"]
    ),
    "Bostan toxumları": ensure_diger_last(["Qarpız toxumu", "Yemiş toxumu", "Boranı toxumu", "Digər"]),
    "Meyvə toxumları": ensure_diger_last(
        [
            "Alma toxumu",
            "Armud toxumu",
            "Şaftalı toxumu",
            "Ərik toxumu",
            "Albalı toxumu",
            "Gilas toxumu",
            "Nar toxumu",
            "Üzüm toxumu",
            "Gavalı toxumu",
            "Heyva toxumu",
            "Digər",
        ]
    ),
    "Digər": ["Digər"],
}

SEED_CATEGORY_ORDER = ensure_diger_last(list(SEED_ITEM_ORDER.keys()))

TOOL_ITEM_ORDER: Dict[str, List[str]] = {
    "Əl Alətləri": ensure_diger_last(["Bel", "Kürək", "Dırmıq", "Balta", "Bıçaq", "Mala", "Digər"]),
    "Suvarma Alətləri": ensure_diger_last(["Şlanq", "Püskürdücü", "Nasos", "Vedrə", "Digər"]),
    "Kənd Texnikası": ensure_diger_last(["Traktor", "Kultivator", "Kotan", "Səpən", "Digər"]),
    "Baxım və Təmir": ensure_diger_last(["Açar dəsti", "Drel", "Çəkic", "Lir", "Digər"]),
    "Digər": ["Digər"],
}

TOOL_CATEGORY_ORDER = ensure_diger_last(list(TOOL_ITEM_ORDER.keys()))
