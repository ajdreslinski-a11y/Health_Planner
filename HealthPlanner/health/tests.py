from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import User as HealthUser


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
