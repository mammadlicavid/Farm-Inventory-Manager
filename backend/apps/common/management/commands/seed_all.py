from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Seeds all default categories and items for the entire application (Animals, Expenses, Seeds, Tools).'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Starting unified database seeding process...'))
        
        commands = [
            ('seed_animals', 'Animals'),
            ('seed_expenses', 'Expenses'),
            ('seed_seeds', 'Seeds'),
            ('seed_tools', 'Tools'),
        ]

        for command_name, module_name in commands:
            self.stdout.write(self.style.NOTICE(f'--- Seeding {module_name} ---'))
            try:
                call_command(command_name)
                self.stdout.write(self.style.SUCCESS(f'Successfully completed seeding {module_name}.'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error seeding {module_name}: {str(e)}'))

        self.stdout.write(self.style.SUCCESS('All database seeding commands executed.'))
