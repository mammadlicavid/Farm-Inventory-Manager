from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from animals.models import Animal, AnimalCategory, AnimalSubCategory
from farm_products.models import FarmProduct, FarmProductCategory, FarmProductItem
from seeds.models import Seed, SeedCategory, SeedItem
from tools.models import Tool, ToolCategory, ToolItem

from .models import Notification, StockAlertRule
from .services import build_stock_alerts, build_stock_rule_catalog, get_stock_items_for_user, sync_stock_alert_notifications


User = get_user_model()


class StockAlertTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="murad", password="secret123")

    def test_new_account_shows_zero_for_important_catalog_items(self):
        seed_category = SeedCategory.objects.create(name="Taxıl toxumları")
        SeedItem.objects.create(category=seed_category, name="Buğda toxumu")
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["low_stock_alerts"])
        self.assertEqual(response.context["low_stock_alerts"][0]["total_display"], 0)

    def test_important_inventory_creates_stock_alert(self):
        seed_category = SeedCategory.objects.create(name="Taxıl toxumları")
        seed_item = SeedItem.objects.create(category=seed_category, name="Arpa toxumu")
        Seed.objects.create(
            item=seed_item,
            quantity="12",
            unit="kg",
            created_by=self.user,
        )

        alerts, _, _ = build_stock_alerts(self.user)

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["item_name"], "Arpa toxumu")

    def test_custom_stock_rule_can_be_saved_from_notifications_page(self):
        category = FarmProductCategory.objects.create(name="Digər")
        item = FarmProductItem.objects.create(category=category, name="Generator yağı", unit="litr")
        FarmProduct.objects.create(
            item=item,
            quantity="6",
            unit="litr",
            created_by=self.user,
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("notifications:list"),
            {
                "action": "add_stock_rule",
                "item_key": f"farm:{item.id}:litr",
                "threshold": "8",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        rule = StockAlertRule.objects.get(created_by=self.user)
        self.assertEqual(rule.item_name, "Generator yağı")
        self.assertContains(response, "Generator yağı")
        self.assertContains(response, "Fərdi limit")

    def test_stock_alert_creates_daily_system_notification(self):
        seed_category = SeedCategory.objects.create(name="Taxıl toxumları")
        SeedItem.objects.create(category=seed_category, name="Buğda toxumu")

        alerts, pending_count = sync_stock_alert_notifications(self.user)

        self.assertTrue(alerts)
        notification = Notification.objects.get(created_by=self.user, source_key="seed:1:kg")
        self.assertEqual(notification.category, "ehtiyat")
        self.assertTrue(notification.is_system_generated)
        self.assertEqual(pending_count, 1)

    def test_dashboard_shows_pending_notification_badge_count(self):
        seed_category = SeedCategory.objects.create(name="Taxıl toxumları")
        SeedItem.objects.create(category=seed_category, name="Buğda toxumu")
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'header-icon-badge')
        self.assertEqual(response.context["pending_notification_count"], 1)

    def test_preloaded_important_items_are_limited_to_four_defaults(self):
        taxil = SeedCategory.objects.create(name="Taxıl toxumları")
        SeedItem.objects.create(category=taxil, name="Buğda toxumu")
        SeedItem.objects.create(category=taxil, name="Arpa toxumu")
        SeedItem.objects.create(category=taxil, name="Çovdar toxumu")

        yem_category = FarmProductCategory.objects.create(name="Yem Bitkiləri")
        FarmProductItem.objects.create(category=yem_category, name="Yonca", unit="kq")
        FarmProductItem.objects.create(category=yem_category, name="Seradella", unit="kq")

        farm_category = FarmProductCategory.objects.create(name="Gübrələr")
        FarmProductItem.objects.create(category=farm_category, name="Mineral gübrə", unit="kq")
        FarmProductItem.objects.create(category=farm_category, name="Kompost", unit="kq")

        alerts, _, _ = build_stock_alerts(self.user)
        names = {alert["item_name"] for alert in alerts}

        self.assertIn("Buğda toxumu", names)
        self.assertIn("Arpa toxumu", names)
        self.assertIn("Yonca", names)
        self.assertIn("Mineral gübrə", names)
        self.assertNotIn("Çovdar toxumu", names)
        self.assertNotIn("Seradella", names)
        self.assertNotIn("Kompost", names)
        self.assertEqual(len(names), 4)

    def test_stale_system_stock_notifications_are_deleted(self):
        Notification.objects.create(
            title="Kompost ehtiyatı kritik həddə düşüb",
            category="ehtiyat",
            due_date="2026-04-03",
            is_completed=True,
            is_system_generated=True,
            source_key="farm:999:kq",
            created_by=self.user,
        )
        Notification.objects.create(
            title="Digər ehtiyatı kritik həddə düşüb",
            category="ehtiyat",
            due_date="2026-04-03",
            is_completed=False,
            is_system_generated=True,
            source_key="farm:1000:kq",
            created_by=self.user,
        )

        seed_category = SeedCategory.objects.create(name="Taxıl toxumları")
        SeedItem.objects.create(category=seed_category, name="Buğda toxumu")

        sync_stock_alert_notifications(self.user)

        remaining_titles = set(Notification.objects.filter(created_by=self.user).values_list("title", flat=True))
        self.assertNotIn("Kompost ehtiyatı kritik həddə düşüb", remaining_titles)
        self.assertNotIn("Digər ehtiyatı kritik həddə düşüb", remaining_titles)

    def test_system_stock_notifications_are_hidden_from_pending_list(self):
        Notification.objects.create(
            title="Buğda ehtiyatı kritik həddə düşüb",
            category="ehtiyat",
            due_date="2026-04-03",
            is_completed=False,
            is_system_generated=True,
            source_key="seed:1:kg",
            created_by=self.user,
        )
        Notification.objects.create(
            title="Manual qeyd",
            category="diger",
            due_date="2026-04-03",
            is_completed=False,
            created_by=self.user,
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("notifications:list"))

        self.assertContains(response, "Manual qeyd")
        self.assertNotContains(response, "Gözləyən (2)")

    def test_stock_rule_catalog_includes_tools_and_animals(self):
        tool_category = ToolCategory.objects.create(name="Texnika")
        tool_item = ToolItem.objects.create(category=tool_category, name="Traktor")

        animal_category = AnimalCategory.objects.create(name="Böyükbaş")
        animal_subcategory = AnimalSubCategory.objects.create(category=animal_category, name="İnək")

        catalog = build_stock_rule_catalog(get_stock_items_for_user(self.user))
        labels = {entry["label"] for entry in catalog}

        self.assertIn("Alət", labels)
        self.assertIn("Heyvan", labels)
        tool_source = next(entry for entry in catalog if entry["label"] == "Alət")
        animal_source = next(entry for entry in catalog if entry["label"] == "Heyvan")
        self.assertEqual(tool_source["categories"][0]["items"][0]["label"], tool_item.name)
        self.assertEqual(animal_source["categories"][0]["items"][0]["label"], animal_subcategory.name)
