import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

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
                            },
                        }
                    ],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Seed.objects.filter(created_by=self.user).count(), 1)
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
        Seed.objects.create(
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
        self.assertEqual(str(seed.quantity), "7.00")

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
        self.assertEqual(str(seed.quantity), "6.00")
        self.assertEqual(response.json()["results"][0]["status"], "failed")
        self.assertIn("Conflict", response.json()["results"][0]["error"])
