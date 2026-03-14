from django.core.management.base import BaseCommand

from tools.models import ToolCategory


class Command(BaseCommand):
    help = "Renames a tool category if it exists."

    def add_arguments(self, parser):
        parser.add_argument("old_name", type=str)
        parser.add_argument("new_name", type=str)

    def handle(self, *args, **options):
        old_name = options["old_name"].strip()
        new_name = options["new_name"].strip()

        if not old_name or not new_name:
            self.stdout.write(self.style.ERROR("Old and new names must be non-empty."))
            return

        qs = ToolCategory.objects.filter(name__iexact=old_name)
        if not qs.exists():
            self.stdout.write(self.style.WARNING(f'Category "{old_name}" not found.'))
            return

        updated = qs.update(name=new_name)
        self.stdout.write(self.style.SUCCESS(f'Renamed {updated} category to "{new_name}".'))
