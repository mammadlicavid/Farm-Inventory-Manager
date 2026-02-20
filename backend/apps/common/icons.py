from __future__ import annotations

from typing import Optional


def get_animal_icon_by_name(name: Optional[str]) -> str:
    """
    Return a Font Awesome class for a given animal subcategory name.
    """
    mapping = {
        "İnək": "fa-solid fa-cow",
        "Dana": "fa-solid fa-cow",
        "Camış": "fa-solid fa-hippo",
        "Qoyun": "fa-solid fa-sheep",
        "Keçi": "fa-solid fa-hand-holding-hand",
        "Toyuq": "fa-solid fa-egg",
        "Hinduşka": "fa-solid fa-turkey",
        "Qaz": "fa-solid fa-dove",
        "Ördək": "fa-solid fa-water",
        "Bildircin": "fa-solid fa-feather-pointed",
        "At": "fa-solid fa-horse",
        "Eşşək": "fa-solid fa-horse-head",
        "Qatır": "fa-solid fa-mule",
    }
    return mapping.get((name or "").strip(), "fa-solid fa-paw")


def get_animal_icon_for_animal(animal) -> str:
    sub = getattr(getattr(animal, "subcategory", None), "name", None)
    return get_animal_icon_by_name(sub)


def get_tool_icon_by_category(name: Optional[str]) -> str:
    """
    Return a Font Awesome class for a given tool category name.
    """
    mapping = {
        "Elektrikli Alətlər": "fa-solid fa-plug",
        "Mexaniki Avadanlıqlar": "fa-solid fa-gear",
        "Əl Alətləri": "fa-solid fa-trowel",
    }
    return mapping.get((name or "").strip(), "fa-solid fa-screwdriver-wrench")


def get_tool_icon_for_tool(tool) -> str:
    category_name = getattr(
        getattr(getattr(tool, "item", None), "category", None),
        "name",
        None,
    )
    return get_tool_icon_by_category(category_name)


def get_seed_icon() -> str:
    return "fa-solid fa-seedling"


def get_seed_icon_for_seed(seed) -> str:  # noqa: ARG001
    return get_seed_icon()


def get_expense_icon(expense) -> str:
    """
    Determine the icon for an Expense.

    Priority:
    1. If linked to Seed / Tool / Animal, reuse that entity's icon.
    2. Otherwise fall back to expense subcategory name mapping.
    """
    obj = getattr(expense, "content_object", None)
    if obj is not None:
        app_label = getattr(getattr(obj, "_meta", None), "app_label", "")
        model_name = getattr(getattr(obj, "_meta", None), "model_name", "")

        if app_label == "animals" and model_name == "animal":
            return get_animal_icon_for_animal(obj)
        if app_label == "tools" and model_name == "tool":
            return get_tool_icon_for_tool(obj)
        if app_label == "seeds" and model_name == "seed":
            return get_seed_icon_for_seed(obj)

    name = getattr(getattr(expense, "subcategory", None), "name", None)
    mapping = {
        "Yem": "fa-solid fa-wheat-awn",
        "Baytarlıq": "fa-solid fa-stethoscope",
        "Peyvəndləmə": "fa-solid fa-syringe",
        "Heyvan alışı": "fa-solid fa-plus-circle",
        "Toxumlar": get_seed_icon(),
        "Gübrə": "fa-solid fa-flask",
        "Pesticidlər": "fa-solid fa-bug-slash",
        "Suvarma": "fa-solid fa-droplet",
        "Maaşlar": "fa-solid fa-money-bill-wave",
        "Sığorta": "fa-solid fa-shield-halved",
        "Yanacaq": "fa-solid fa-gas-pump",
        "Təmir və Baxım": "fa-solid fa-screwdriver-wrench",
        "Texnika alışı": "fa-solid fa-tractor",
        "Elektrik": "fa-solid fa-bolt",
        "Su": "fa-solid fa-faucet-drip",
        "Tikinti": "fa-solid fa-trowel-bricks",
        "Nəqliyyat": "fa-solid fa-truck",
        "Qablaşdırma": "fa-solid fa-box-open",
        "Vergilər": "fa-solid fa-file-invoice-dollar",
        "Kredit faizləri": "fa-solid fa-percent",
    }
    return mapping.get((name or "").strip(), "fa-solid fa-receipt")

