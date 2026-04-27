import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from expenses.models import Expense
from incomes.models import Income
from seeds.models import Seed, SeedCategory, SeedItem

from .models import DeviceSyncState


class SyncPushTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="farmer",
            password="testpass123",
        )
        self.client.force_login(self.user)
        self.url = reverse("sync:push")

    def test_sync_push_creates_seed_and_updates_device_state(self):
        category = SeedCategory.objects.create(name="Taxıl toxumları")
        item = SeedItem.objects.create(category=category, name="Buğda")

        response = self.client.post(
            self.url,
            data=json.dumps(
                {
                    "device_id": "device-1",
                    "operations": [
                        {
                            "id": "op-seed-1",
                            "entity": "seed",
                            "action": "create",
                            "data": {
                                "item": str(item.id),
                                "quantity": "12.5",
                                "unit": "kg",
                                "price": "50",
                                "date": "2026-03-22",
                                "time": "14:35",
                            },
                        }
                    ],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Seed.objects.filter(created_by=self.user).count(), 1)
        seed = Seed.objects.get(created_by=self.user)
        self.assertEqual(seed.time.strftime("%H:%M"), "14:35")
        state = DeviceSyncState.objects.get(user=self.user, device_id="device-1")
        self.assertIsNotNone(state.last_synced_at)
        self.assertEqual(response.json()["results"][0]["status"], "completed")

    def test_sync_push_deduplicates_completed_operation(self):
        payload = {
            "device_id": "device-2",
            "operations": [
                {
                    "id": "op-expense-1",
                    "entity": "expense",
                    "action": "create",
                    "data": {
                        "manual_name": "Yanacaq",
                        "amount": "25.40",
                        "date": "2026-03-22",
                    },
                }
            ],
        }

        first_response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        second_response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(self.user.expenses_created.count(), 1)
        self.assertTrue(second_response.json()["results"][0]["deduplicated"])

    def test_sync_push_creates_income(self):
        response = self.client.post(
            self.url,
            data=json.dumps(
                {
                    "device_id": "device-3",
                    "operations": [
                        {
                            "id": "op-income-1",
                            "entity": "income",
                            "action": "create",
                            "data": {
                                "category": "Digər",
                                "manual_name": "Əl satış",
                                "quantity": "3",
                                "unit": "ədəd",
                                "amount": "12",
                                "date": "2026-03-22",
                            },
                        }
                    ],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Income.objects.filter(created_by=self.user).count(), 1)
        self.assertEqual(Income.objects.get(created_by=self.user).item_name, "Əl satış")

    def test_sync_push_updates_stock(self):
        category = SeedCategory.objects.create(name="Taxıl toxumları")
        item = SeedItem.objects.create(category=category, name="Buğda")
        seed = Seed.objects.create(
            item=item,
            quantity="4",
            unit="kg",
            price="0",
            created_by=self.user,
        )

        response = self.client.post(
            self.url,
            data=json.dumps(
                {
                    "device_id": "device-4",
                    "operations": [
                        {
                            "id": "op-stock-1",
                            "entity": "stock",
                            "action": "update",
                            "data": {
                                "update_type": "seed",
                                "update_id": str(item.id),
                                "target_quantity": "10",
                                "date": "2026-03-25",
                                "time": "10:45",
                            },
                        }
                    ],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Seed.objects.filter(created_by=self.user, item=item).count(), 2)
        total_quantity = sum(seed.quantity for seed in Seed.objects.filter(created_by=self.user, item=item))
        self.assertEqual(total_quantity, 10)
        adjustment = Seed.objects.exclude(pk=seed.pk).get(created_by=self.user, item=item)
        self.assertEqual(adjustment.date.isoformat(), "2026-03-25")
        self.assertEqual(adjustment.time.strftime("%H:%M"), "10:45")

    def test_sync_push_updates_seed(self):
        category = SeedCategory.objects.create(name="Taxıl toxumları")
        item = SeedItem.objects.create(category=category, name="Buğda")
        seed = Seed.objects.create(
            item=item,
            quantity="4",
            unit="kg",
            price="0",
            created_by=self.user,
        )

        response = self.client.post(
            self.url,
            data=json.dumps(
                {
                    "device_id": "device-5",
                    "operations": [
                        {
                            "id": "op-seed-update-1",
                            "entity": "seed",
                            "action": "update",
                            "data": {
                                "record_id": str(seed.id),
                                "record_version": seed.updated_at.isoformat(),
                                "item": str(item.id),
                                "quantity": "7",
                                "unit": "kg",
                                "price": "0",
                                "zero_price_source": "existing",
                                "date": "2026-03-22",
                                "time": "09:15",
                            },
                        }
                    ],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        seed.refresh_from_db()
        self.assertEqual(str(seed.quantity), "7.0000")
        self.assertEqual(seed.zero_price_source, "existing")
        self.assertEqual(seed.time.strftime("%H:%M"), "09:15")

    def test_sync_push_rejects_zero_price_stock_without_source(self):
        category = SeedCategory.objects.create(name="Taxıl toxumları")
        item = SeedItem.objects.create(category=category, name="Buğda")

        response = self.client.post(
            self.url,
            data=json.dumps(
                {
                    "device_id": "device-zero-source",
                    "operations": [
                        {
                            "id": "op-seed-zero-source",
                            "entity": "seed",
                            "action": "create",
                            "data": {
                                "item": str(item.id),
                                "quantity": "3",
                                "unit": "kg",
                                "price": "0",
                                "date": "2026-03-22",
                            },
                        }
                    ],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["status"], "failed")
        self.assertIn("Məbləğ 0", response.json()["results"][0]["error"])
        self.assertFalse(Seed.objects.filter(created_by=self.user).exists())

    def test_sync_push_updates_expense_date_and_time(self):
        expense = Expense.objects.create(
            title="Yanacaq",
            manual_name="Yanacaq",
            amount="10",
            date="2026-03-21",
            created_by=self.user,
        )

        response = self.client.post(
            self.url,
            data=json.dumps(
                {
                    "device_id": "device-expense-time",
                    "operations": [
                        {
                            "id": "op-expense-time",
                            "entity": "expense",
                            "action": "update",
                            "data": {
                                "record_id": str(expense.id),
                                "record_version": expense.updated_at.isoformat(),
                                "title": "Yanacaq",
                                "manual_name": "Yanacaq",
                                "amount": "12.50",
                                "date": "2026-03-24",
                                "time": "16:20",
                            },
                        }
                    ],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["status"], "completed")
        expense.refresh_from_db()
        self.assertEqual(expense.date.isoformat(), "2026-03-24")
        self.assertEqual(expense.time.strftime("%H:%M"), "16:20")

    def test_sync_push_quick_entries_use_queued_date_and_time(self):
        expense_response = self.client.post(
            self.url,
            data=json.dumps(
                {
                    "device_id": "device-quick-expense-time",
                    "operations": [
                        {
                            "id": "op-quick-expense-time",
                            "entity": "quick_expense",
                            "action": "custom_amount",
                            "data": {
                                "action": "custom_amount",
                                "amount": "7.25",
                                "date": "2026-03-26",
                                "time": "08:05",
                            },
                        }
                    ],
                }
            ),
            content_type="application/json",
        )

        income_response = self.client.post(
            self.url,
            data=json.dumps(
                {
                    "device_id": "device-quick-income-time",
                    "operations": [
                        {
                            "id": "op-quick-income-time",
                            "entity": "quick_income",
                            "action": "custom_amount",
                            "data": {
                                "action": "custom_amount",
                                "amount": "9.50",
                                "date": "2026-03-27",
                                "time": "19:40",
                            },
                        }
                    ],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(expense_response.status_code, 200)
        self.assertEqual(income_response.status_code, 200)
        self.assertEqual(expense_response.json()["results"][0]["status"], "completed")
        self.assertEqual(income_response.json()["results"][0]["status"], "completed")

        expense = Expense.objects.get(created_by=self.user, amount="7.25")
        income = Income.objects.get(created_by=self.user, amount="9.50")
        self.assertEqual(expense.date.isoformat(), "2026-03-26")
        self.assertEqual(expense.time.strftime("%H:%M"), "08:05")
        self.assertEqual(income.date.isoformat(), "2026-03-27")
        self.assertEqual(income.time.strftime("%H:%M"), "19:40")

    def test_sync_push_deletes_seed(self):
        category = SeedCategory.objects.create(name="Taxıl toxumları")
        item = SeedItem.objects.create(category=category, name="Buğda")
        seed = Seed.objects.create(
            item=item,
            quantity="4",
            unit="kg",
            price="0",
            created_by=self.user,
        )

        response = self.client.post(
            self.url,
            data=json.dumps(
                {
                    "device_id": "device-6",
                    "operations": [
                        {
                            "id": "op-seed-delete-1",
                            "entity": "seed",
                            "action": "delete",
                            "data": {
                                "record_id": str(seed.id),
                                "record_version": seed.updated_at.isoformat(),
                            },
                        }
                    ],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Seed.objects.filter(id=seed.id).exists())

    def test_sync_push_rejects_stale_seed_update(self):
        category = SeedCategory.objects.create(name="Taxıl toxumları")
        item = SeedItem.objects.create(category=category, name="Buğda")
        seed = Seed.objects.create(
            item=item,
            quantity="4",
            unit="kg",
            price="0",
            created_by=self.user,
        )
        stale_version = seed.updated_at.isoformat()
        seed.quantity = "6"
        seed.save()

        response = self.client.post(
            self.url,
            data=json.dumps(
                {
                    "device_id": "device-7",
                    "operations": [
                        {
                            "id": "op-seed-stale-1",
                            "entity": "seed",
                            "action": "update",
                            "data": {
                                "record_id": str(seed.id),
                                "record_version": stale_version,
                                "item": str(item.id),
                                "quantity": "7",
                                "unit": "kg",
                                "price": "0",
                                "date": "2026-03-22",
                            },
                        }
                    ],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        seed.refresh_from_db()
        self.assertEqual(str(seed.quantity), "6.0000")
        self.assertEqual(response.json()["results"][0]["status"], "failed")
        self.assertIn("Conflict", response.json()["results"][0]["error"])
