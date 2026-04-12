from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from animals.models import Animal, AnimalCategory, AnimalSubCategory
from expenses.models import Expense
from farm_products.models import FarmProduct, FarmProductCategory, FarmProductItem
from incomes.models import Income
from seeds.models import Seed, SeedCategory, SeedItem
from tools.models import Tool, ToolCategory, ToolItem


class DashboardViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            username="farmer",
            password="secret123",
            first_name="Murad",
        )
        self.client.force_login(self.user)

    def test_dashboard_builds_farmer_friendly_overview_metrics(self):
        seed_category = SeedCategory.objects.create(name="Taxıl")
        seed_item = SeedItem.objects.create(category=seed_category, name="Buğda")
        tool_category = ToolCategory.objects.create(name="Əl alətləri")
        tool_item = ToolItem.objects.create(category=tool_category, name="Kürək")
        animal_category = AnimalCategory.objects.create(name="Mal-qara")
        animal_subcategory = AnimalSubCategory.objects.create(category=animal_category, name="İnək")
        farm_category = FarmProductCategory.objects.create(name="Süd məhsulları")
        farm_item = FarmProductItem.objects.create(category=farm_category, name="Süd", unit="litr")

        Seed.objects.create(item=seed_item, quantity=5, unit="kg", created_by=self.user)
        Tool.objects.create(item=tool_item, quantity=2, created_by=self.user)
        Animal.objects.create(subcategory=animal_subcategory, quantity=3, gender="disi", created_by=self.user)
        FarmProduct.objects.create(item=farm_item, quantity=12, unit="litr", created_by=self.user)
        Income.objects.create(
            category="Süd məhsulları",
            item_name="Süd",
            quantity=12,
            unit="litr",
            amount=240,
            created_by=self.user,
        )
        Expense.objects.create(title="Yem", amount=80, created_by=self.user)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["show_onboarding"])
        self.assertEqual(response.context["overview"]["stock_groups"], 4)
        self.assertEqual(response.context["overview"]["weekly_income_display"], "240.00")
        self.assertEqual(response.context["overview"]["weekly_expenses_display"], "80.00")
        self.assertEqual(response.context["overview"]["weekly_balance_display"], "160.00")

    def test_dashboard_shows_onboarding_for_new_user_without_records(self):
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["show_onboarding"])
        self.assertEqual(response.context["overview"]["stock_groups"], 0)
        self.assertEqual(response.context["overview"]["weekly_income_display"], "0.00")
        self.assertEqual(response.context["overview"]["weekly_expenses_display"], "0.00")

    def test_calendar_page_groups_daily_activity_for_selected_month(self):
        seed_category = SeedCategory.objects.create(name="Taxıl")
        seed_item = SeedItem.objects.create(category=seed_category, name="Buğda")

        Seed.objects.create(
            item=seed_item,
            quantity=5,
            unit="kg",
            created_by=self.user,
            date=date(2026, 4, 10),
        )
        Income.objects.create(
            category="Taxıl",
            item_name="Buğda",
            quantity=2,
            unit="kg",
            amount=36,
            created_by=self.user,
            date=date(2026, 4, 10),
        )
        expense = Expense.objects.create(
            title="Yanacaq",
            amount=12,
            created_by=self.user,
        )
        expense.date = date(2026, 4, 11)
        expense.save(update_fields=["date"])

        response = self.client.get(
            reverse("calendar"),
            {
                "month": "2026-04",
                "day": "2026-04-10",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["calendar_data"]["active_month_key"], "2026-04")
        self.assertEqual(response.context["calendar_data"]["active_day_count"], 2)
        self.assertEqual(response.context["calendar_data"]["monthly_stock_actions"], 1)
        self.assertEqual(response.context["calendar_data"]["monthly_income"], Decimal("36"))
        self.assertEqual(response.context["calendar_data"]["monthly_expense"], Decimal("12"))
        self.assertEqual(response.context["calendar_data"]["selected_day"]["summary"]["total"], 2)
        self.assertEqual(response.context["calendar_data"]["selected_day"]["summary"]["stock_in"], 1)
        self.assertEqual(response.context["calendar_data"]["selected_day"]["summary"]["income"], 1)

    def test_calendar_keeps_only_origin_entry_for_linked_income_and_expense_records(self):
        seed_category = SeedCategory.objects.create(name="Taxıl")
        seed_item = SeedItem.objects.create(category=seed_category, name="Buğda")

        purchased_seed = Seed.objects.create(
            item=seed_item,
            quantity=4,
            unit="kg",
            price=18,
            created_by=self.user,
            date=date(2026, 4, 10),
        )
        linked_expense = Expense.objects.create(
            title="Toxum alışı: Buğda",
            amount=18,
            created_by=self.user,
        )
        linked_expense.date = date(2026, 4, 10)
        linked_expense.content_object = purchased_seed
        linked_expense.save(update_fields=["date", "content_type", "object_id"])

        income = Income.objects.create(
            category="Taxıl",
            item_name="Buğda",
            quantity=2,
            unit="kg",
            amount=24,
            created_by=self.user,
            date=date(2026, 4, 10),
        )
        generated_stock = Seed.objects.create(
            item=seed_item,
            quantity=-2,
            unit="kg",
            price=24,
            additional_info="Gəlir satışı",
            created_by=self.user,
            date=date(2026, 4, 10),
        )
        income.content_object = generated_stock
        income.save(update_fields=["content_type", "object_id"])

        response = self.client.get(
            reverse("calendar"),
            {
                "month": "2026-04",
                "day": "2026-04-10",
            },
        )

        activities = response.context["calendar_data"]["selected_day"]["activities"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(activities), 2)
        self.assertEqual(sum(1 for activity in activities if activity["kind"] == "stock-in"), 1)
        self.assertEqual(sum(1 for activity in activities if activity["kind"] == "income"), 1)
        self.assertEqual(sum(1 for activity in activities if activity["kind"] == "expense"), 0)
        self.assertEqual(response.context["calendar_data"]["selected_day"]["expense_total"], Decimal("18"))
        self.assertEqual(response.context["calendar_data"]["selected_day"]["income_total"], Decimal("24"))
