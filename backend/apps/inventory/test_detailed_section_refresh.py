from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from animals.models import Animal, AnimalCategory, AnimalSubCategory
from farm_products.models import FarmProduct, FarmProductCategory, FarmProductItem
from seeds.models import Seed, SeedCategory, SeedItem
from tools.models import Tool, ToolCategory, ToolItem


class DetailedSectionRefreshTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="farmer", password="StrongPass123!")
        self.client.force_login(self.user)
        self.today = timezone.localdate().isoformat()

    def test_animal_create_refreshes_list_and_shows_zero_price_source_badge(self):
        category = AnimalCategory.objects.create(name="İnəklər")
        subcategory = AnimalSubCategory.objects.create(category=category, name="Süd inəyi")

        self.client.get(reverse("animals:animal_list"))
        response = self.client.post(
            reverse("animals:animal_create"),
            {
                "subcategory": str(subcategory.id),
                "quantity": "1",
                "gender": "erkek",
                "price": "",
                "zero_price_source": "existing",
                "date": self.today,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("_ui=", response["Location"])

        animal = Animal.objects.get(created_by=self.user)
        self.assertEqual(animal.zero_price_source, "existing")

        page = self.client.get(response["Location"])
        self.assertContains(page, "Süd inəyi")
        self.assertContains(page, "Əvvəlcədən məndə var idi")

    def test_seed_create_refreshes_list_and_shows_zero_price_source_badge(self):
        category = SeedCategory.objects.create(name="Taxıl toxumları")
        item = SeedItem.objects.create(category=category, name="Buğda")

        self.client.get(reverse("seeds:seed_list"))
        response = self.client.post(
            reverse("seeds:seed_create"),
            {
                "item": str(item.id),
                "quantity": "5",
                "unit": "kg",
                "price": "",
                "zero_price_source": "free",
                "date": self.today,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("_ui=", response["Location"])

        seed = Seed.objects.get(created_by=self.user)
        self.assertEqual(seed.zero_price_source, "free")

        page = self.client.get(response["Location"])
        self.assertContains(page, "Buğda")
        self.assertContains(page, "Pulsuz gəlib / hədiyyədir")

    def test_tool_create_refreshes_list_and_shows_zero_price_source_badge(self):
        category = ToolCategory.objects.create(name="Əl alətləri")
        item = ToolItem.objects.create(category=category, name="Kürək")

        self.client.get(reverse("tools:tool_list"))
        response = self.client.post(
            reverse("tools:tool_create"),
            {
                "item": str(item.id),
                "quantity": "1",
                "price": "",
                "zero_price_source": "internal",
                "date": self.today,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("_ui=", response["Location"])

        tool = Tool.objects.get(created_by=self.user)
        self.assertEqual(tool.zero_price_source, "internal")

        page = self.client.get(response["Location"])
        self.assertContains(page, "Kürək")
        self.assertContains(page, "Təsərrüfat daxilində yaranıb")

    def test_farm_product_create_refreshes_list_and_shows_zero_price_source_badge(self):
        category = FarmProductCategory.objects.create(name="Tərəvəz")
        item = FarmProductItem.objects.create(category=category, name="Pomidor", unit="kq")

        self.client.get(reverse("farm_products:product_list"))
        response = self.client.post(
            reverse("farm_products:product_create"),
            {
                "item": str(item.id),
                "quantity": "8",
                "unit": "kq",
                "price": "",
                "zero_price_source": "other",
                "date": self.today,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("_ui=", response["Location"])

        product = FarmProduct.objects.get(created_by=self.user)
        self.assertEqual(product.zero_price_source, "other")

        page = self.client.get(response["Location"])
        self.assertContains(page, "Pomidor")
        self.assertContains(page, "Digər")
