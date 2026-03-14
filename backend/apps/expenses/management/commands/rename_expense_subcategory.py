from django.core.management.base import BaseCommand
from expenses.models import ExpenseSubCategory


class Command(BaseCommand):
    help = "Rename an expense subcategory (and keep the same category)."

    def add_arguments(self, parser):
        parser.add_argument("--from", dest="from_name", required=True, help="Old subcategory name")
        parser.add_argument("--to", dest="to_name", required=True, help="New subcategory name")

    def handle(self, *args, **kwargs):
        from_name = kwargs["from_name"]
        to_name = kwargs["to_name"]

        qs = ExpenseSubCategory.objects.filter(name=from_name)
        count = qs.count()
        if count == 0:
            self.stdout.write(self.style.WARNING(f"No subcategory found with name '{from_name}'"))
            return

        qs.update(name=to_name)
        self.stdout.write(self.style.SUCCESS(f"Renamed {count} subcategory(ies): '{from_name}' -> '{to_name}'"))
