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

    def test_recent_users_card_has_prompt_link(self):
        response = self.client.get(reverse("health:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("health:create_recent_user"))
        self.assertContains(response, "Add a recent user")

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
