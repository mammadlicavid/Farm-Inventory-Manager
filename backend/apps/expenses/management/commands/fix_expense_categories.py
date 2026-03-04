from django.core.management.base import BaseCommand
from expenses.models import Expense, ExpenseSubCategory


class Command(BaseCommand):
    help = "Backfill expense subcategories for records missing category/subcategory info."

    def handle(self, *args, **kwargs):
        subcats = ExpenseSubCategory.objects.select_related("category").all()
        subcat_lookup = {s.name.lower(): s for s in subcats}

        def resolve_by_name(name: str):
            if not name:
                return None
            return subcat_lookup.get(name.lower())

        def resolve_by_title(title: str):
            if not title:
                return None
            title_lower = title.lower().strip()
            # Direct match
            direct = resolve_by_name(title_lower)
            if direct:
                return direct

            # Common prefixes
            if title_lower.startswith("toxum alışı"):
                return resolve_by_name("toxumlar")
            if title_lower.startswith("alət alışı"):
                return resolve_by_name("texnika alışı")
            if title_lower.startswith("heyvan alışı"):
                return resolve_by_name("heyvan alışı")

            # Try to match after colon (e.g. "Toxum alışı: Ərik")
            if ":" in title_lower:
                base = title_lower.split(":", 1)[0].strip()
                return resolve_by_name(base)

            return None

        qs = Expense.objects.filter(subcategory__isnull=True)
        updated = 0
        manual_filled = 0

        for exp in qs:
            match = resolve_by_name(exp.manual_name) or resolve_by_title(exp.title)
            if match:
                exp.subcategory = match
                exp.manual_name = None
                exp.save(update_fields=["subcategory", "manual_name"])
                updated += 1
                continue

            if not exp.manual_name and exp.title:
                exp.manual_name = exp.title
                exp.save(update_fields=["manual_name"])
                manual_filled += 1

        self.stdout.write(self.style.SUCCESS(f"Updated subcategory for {updated} expenses."))
        self.stdout.write(self.style.SUCCESS(f"Filled manual_name for {manual_filled} expenses."))
