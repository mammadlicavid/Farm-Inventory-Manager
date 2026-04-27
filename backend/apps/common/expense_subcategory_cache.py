"""Cached helpers for frequently-queried ExpenseSubCategory rows.

Every CRUD view that creates automatic expense records (seed, tool, animal,
farm-product) needs to look up the same subcategory row. Caching it in the
LocMem cache avoids a DB round-trip on every single add/update/delete.
"""

from django.core.cache import cache

_SUBCAT_CACHE_TTL = 60 * 60  # 1 hour


def get_expense_subcategory(name: str, *, icontains: bool = False):
    """Return an ExpenseSubCategory by *name* (cached).

    Parameters
    ----------
    name : str
        The subcategory name to look up.
    icontains : bool
        If True, use ``name__icontains`` instead of exact match.
    """
    cache_key = f"expense-subcat:v1:{name.lower()}:{'ic' if icontains else 'eq'}"
    result = cache.get(cache_key)
    if result is not None:
        # sentinel: we store False when the row does not exist
        return result if result is not False else None

    from expenses.models import ExpenseSubCategory

    if icontains:
        row = ExpenseSubCategory.objects.filter(name__icontains=name).first()
    else:
        row = ExpenseSubCategory.objects.filter(name=name).first()

    cache.set(cache_key, row if row else False, _SUBCAT_CACHE_TTL)
    return row
