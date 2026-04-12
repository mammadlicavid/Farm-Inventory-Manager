from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from expenses.models import Expense, ExpenseCategory, ExpenseSubCategory
from incomes.models import Income


class ReportsViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="report-user",
            password="secret123",
        )
        self.client.force_login(self.user)

    def _create_expense(self, *, amount, record_date, category_name="Yem", subcategory_name="Quru yem", title="Yem alışı"):
        category, _ = ExpenseCategory.objects.get_or_create(name=category_name)
        subcategory, _ = ExpenseSubCategory.objects.get_or_create(
            category=category,
            name=subcategory_name,
        )
        expense = Expense.objects.create(
            title=title,
            amount=amount,
            subcategory=subcategory,
            created_by=self.user,
        )
        expense.date = record_date
        expense.save(update_fields=["date"])
        return expense

    def test_reports_list_builds_filtered_financial_summary(self):
        Income.objects.create(
            category="Süd məhsulları",
            item_name="Süd",
            quantity=12,
            unit="litr",
            amount=180,
            created_by=self.user,
            date=date(2026, 4, 4),
        )
        Income.objects.create(
            category="Süd məhsulları",
            item_name="Pendir",
            quantity=4,
            unit="kq",
            amount=120,
            created_by=self.user,
            date=date(2026, 4, 12),
        )
        self._create_expense(amount=70, record_date=date(2026, 4, 5))
        self._create_expense(amount=30, record_date=date(2026, 4, 14), category_name="Yanacaq", subcategory_name="Dizel", title="Yanacaq")

        response = self.client.get(
            reverse("reports:list"),
            {
                "date_from": "2026-04-01",
                "date_to": "2026-04-30",
                "purpose": "loan",
                "group_by": "day",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["kpis"]["total_income_display"], "300.00")
        self.assertEqual(response.context["kpis"]["total_expense_display"], "100.00")
        self.assertEqual(response.context["kpis"]["net_profit_display"], "200.00")
        self.assertEqual(response.context["filters"]["selected_purpose"], "loan")
        self.assertEqual(response.context["filters"]["resolved_group_by"], "day")
        self.assertEqual(response.context["tax"]["total_due_display"], "21.60")
        self.assertEqual(response.context["tax"]["reference_vat_amount_display"], "54.00")
        self.assertIn("Aprel", response.context["chart"]["points"][0]["label"])
        self.assertEqual(len(response.context["product_rows"]), 2)
        self.assertGreaterEqual(len(response.context["chart"]["points"]), 2)

    def test_reports_pdf_downloads_binary_pdf(self):
        Income.objects.create(
            category="Meyvə",
            item_name="Alma",
            quantity=10,
            unit="kq",
            amount=55,
            created_by=self.user,
            date=date(2026, 3, 3),
        )

        response = self.client.get(
            reverse("reports:pdf"),
            {
                "date_from": "2026-03-01",
                "date_to": "2026-03-31",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertIn(".pdf", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF-"))
        self.assertGreater(len(response.content), 20000)

    def test_reports_expense_breakdown_uses_resolved_category_for_linked_expense_titles(self):
        category = ExpenseCategory.objects.create(name="Bitkiçilik")
        ExpenseSubCategory.objects.create(category=category, name="Toxumlar")
        Expense.objects.create(
            title="Toxum alışı: Buğda toxumu",
            amount=32,
            manual_name="Toxum alışı",
            created_by=self.user,
            date=date(2026, 4, 6),
        )

        response = self.client.get(
            reverse("reports:list"),
            {
                "date_from": "2026-04-01",
                "date_to": "2026-04-30",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["expense_breakdown"][0]["name"], "Bitkiçilik")
