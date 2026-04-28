from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Food, Meal, MealItem, User as HealthUser


class RecentUserFlowTests(TestCase):
    def setUp(self):
        self.account = get_user_model().objects.create_user(
            email="owner@example.com",
            name="Owner",
            age=30,
            height="5.10",
            weight="170.00",
            password="testpass123",
        )
        self.other_account = get_user_model().objects.create_user(
            email="second-owner@example.com",
            name="Second Owner",
            age=30,
            height="5.10",
            weight="170.00",
            password="testpass123",
        )
        self.assertTrue(
            self.client.login(username="owner@example.com", password="testpass123")
        )
        self.recent_user = HealthUser.objects.create(
            name="Jordan Lee",
            email="jordan@example.com",
            age=32,
            height="5.11",
            weight="172.00",
            password="!",
            account=self.account,
        )
        self.other_recent_user = HealthUser.objects.create(
            name="Morgan Tate",
            email="morgan@example.com",
            age=29,
            height="5.07",
            weight="145.00",
            password="!",
            account=self.other_account,
        )

    def test_recent_users_card_only_shows_users_for_signed_in_account(self):
        response = self.client.get(reverse("health:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("health:create_recent_user"))
        self.assertContains(response, "Add a recent user")
        self.assertContains(response, "Jordan Lee")
        self.assertNotContains(response, "Morgan Tate")
        self.assertContains(
            response,
            reverse("health:edit_recent_user", args=[self.recent_user.user_id]),
        )
        self.assertNotContains(
            response,
            reverse("health:edit_recent_user", args=[self.other_recent_user.user_id]),
        )

    def test_submitting_recent_user_form_assigns_current_account(self):
        response = self.client.post(
            reverse("health:create_recent_user"),
            {
                "name": "Taylor Brooks",
                "email": "taylor@example.com",
                "age": 28,
                "height": "5.09",
                "weight": "154.50",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("health:dashboard"))
        self.assertContains(response, "Taylor Brooks")
        self.assertTrue(
            HealthUser.objects.filter(
                email="taylor@example.com",
                account=self.account,
            ).exists()
        )
        self.assertFalse(
            HealthUser.objects.get(
                email="taylor@example.com",
                account=self.account,
            ).has_usable_password()
        )

    def test_editing_recent_user_updates_dashboard_name(self):
        response = self.client.post(
            reverse("health:edit_recent_user", args=[self.recent_user.user_id]),
            {
                "name": "Jordan Smith",
                "email": "jordan@example.com",
                "age": 33,
                "height": "6.00",
                "weight": "170.50",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("health:dashboard"))
        self.assertContains(response, "Jordan Smith")
        self.recent_user.refresh_from_db()
        self.assertEqual(self.recent_user.name, "Jordan Smith")
        self.assertEqual(self.recent_user.age, 33)

    def test_cannot_edit_recent_user_from_another_account(self):
        response = self.client.get(
            reverse("health:edit_recent_user", args=[self.other_recent_user.user_id])
        )

        self.assertEqual(response.status_code, 404)


class MealFlowTests(TestCase):
    def setUp(self):
        self.account = get_user_model().objects.create_user(
            email="meal-owner@example.com",
            name="Meal Owner",
            age=31,
            height="5.08",
            weight="162.00",
            password="testpass123",
        )
        self.other_account = get_user_model().objects.create_user(
            email="other-meal-owner@example.com",
            name="Other Meal Owner",
            age=29,
            height="5.09",
            weight="168.00",
            password="testpass123",
        )
        self.assertTrue(
            self.client.login(username="meal-owner@example.com", password="testpass123")
        )
        self.meal = Meal.objects.create(
            user=self.account,
            name="Chicken Bowl",
            meal_type="lunch",
            date="2026-04-27",
            time="12:15",
        )
        self.other_meal = Meal.objects.create(
            user=self.other_account,
            name="Other User Meal",
            meal_type="dinner",
            date="2026-04-27",
            time="18:45",
        )
        self.food = Food.objects.create(
            name="Chicken Breast",
            calories_per_100g=Decimal("165.00"),
            protein_per_100g=Decimal("31.00"),
            carbs_per_100g=Decimal("0.00"),
            fat_per_100g=Decimal("3.60"),
            fiber_per_100g=Decimal("0.00"),
            sugar_per_100g=Decimal("0.00"),
        )
        self.other_food = Food.objects.create(
            name="Rice",
            calories_per_100g=Decimal("130.00"),
            protein_per_100g=Decimal("2.70"),
            carbs_per_100g=Decimal("28.00"),
            fat_per_100g=Decimal("0.30"),
            fiber_per_100g=Decimal("0.40"),
            sugar_per_100g=Decimal("0.10"),
        )
        self.meal_item = MealItem.objects.create(
            meal=self.meal,
            food=self.food,
            quantity_grams="120.00",
        )
        self.other_meal_item = MealItem.objects.create(
            meal=self.other_meal,
            food=self.other_food,
            quantity_grams="150.00",
        )

    def test_dashboard_latest_meals_includes_edit_link_and_delete_button(self):
        response = self.client.get(reverse("health:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("health:edit_meal", args=[self.meal.meal_id]))
        self.assertContains(
            response, reverse("health:delete_meal", args=[self.meal.meal_id])
        )

    def test_dashboard_latest_meal_items_includes_edit_link_and_delete_button(self):
        response = self.client.get(reverse("health:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, reverse("health:edit_meal_item", args=[self.meal_item.meal_item_id])
        )
        self.assertContains(
            response,
            reverse("health:delete_meal_item", args=[self.meal_item.meal_item_id]),
        )

    def test_editing_meal_updates_it(self):
        response = self.client.post(
            reverse("health:edit_meal", args=[self.meal.meal_id]),
            {
                "name": "Updated Chicken Bowl",
                "meal_type": "dinner",
                "date": "2026-04-28",
                "time": "19:00",
                "notes": "Updated notes",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("health:dashboard"))
        self.meal.refresh_from_db()
        self.assertEqual(self.meal.name, "Updated Chicken Bowl")
        self.assertEqual(self.meal.meal_type, "dinner")

    def test_deleting_meal_removes_it(self):
        response = self.client.post(
            reverse("health:delete_meal", args=[self.meal.meal_id]),
            follow=True,
        )

        self.assertRedirects(response, reverse("health:dashboard"))
        self.assertFalse(Meal.objects.filter(meal_id=self.meal.meal_id).exists())

    def test_cannot_edit_or_delete_other_users_meal(self):
        edit_response = self.client.get(
            reverse("health:edit_meal", args=[self.other_meal.meal_id])
        )
        delete_response = self.client.post(
            reverse("health:delete_meal", args=[self.other_meal.meal_id])
        )

        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)

    def test_editing_meal_item_updates_it(self):
        response = self.client.post(
            reverse("health:edit_meal_item", args=[self.meal_item.meal_item_id]),
            {
                "food": self.other_food.pk,
                "quantity_grams": "200.00",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("health:dashboard"))
        self.meal_item.refresh_from_db()
        self.assertEqual(self.meal_item.food_id, self.other_food.pk)
        self.assertEqual(str(self.meal_item.quantity_grams), "200.00")

    def test_deleting_meal_item_removes_it(self):
        response = self.client.post(
            reverse("health:delete_meal_item", args=[self.meal_item.meal_item_id]),
            follow=True,
        )

        self.assertRedirects(response, reverse("health:dashboard"))
        self.assertFalse(
            MealItem.objects.filter(meal_item_id=self.meal_item.meal_item_id).exists()
        )

    def test_cannot_edit_or_delete_other_users_meal_item(self):
        edit_response = self.client.get(
            reverse("health:edit_meal_item", args=[self.other_meal_item.meal_item_id])
        )
        delete_response = self.client.post(
            reverse("health:delete_meal_item", args=[self.other_meal_item.meal_item_id])
        )

        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
