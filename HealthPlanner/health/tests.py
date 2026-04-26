from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import User as HealthUser


class RecentUserFlowTests(TestCase):
    def setUp(self):
        self.account = get_user_model().objects.create_user(
            username="owner",
            email="owner@example.com",
            password="testpass123",
        )
        self.assertTrue(
            self.client.login(username="owner", password="testpass123")
        )
        self.recent_user = HealthUser.objects.create(
            name="Jordan Lee",
            email="jordan@example.com",
            age=32,
            height="5.11",
            weight="172.00",
            password="!",
        )

    def test_recent_users_card_has_prompt_link(self):
        response = self.client.get(reverse("health:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("health:create_recent_user"))
        self.assertContains(response, "Add a recent user")
        self.assertContains(
            response,
            reverse("health:edit_recent_user", args=[self.recent_user.user_id]),
        )

    def test_submitting_recent_user_form_shows_name_on_dashboard(self):
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
        self.assertTrue(HealthUser.objects.filter(email="taylor@example.com").exists())
        self.assertFalse(
            HealthUser.objects.get(email="taylor@example.com").has_usable_password()
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
