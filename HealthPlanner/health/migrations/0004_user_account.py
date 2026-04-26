from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def assign_existing_recent_users_to_single_account(apps, schema_editor):
    recent_user_model = apps.get_model("health", "User")
    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    account_model = apps.get_model(app_label, model_name)
    accounts = list(account_model.objects.order_by("pk")[:2])

    if len(accounts) == 1:
        recent_user_model.objects.filter(account__isnull=True).update(
            account_id=accounts[0].pk
        )


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("health", "0003_alter_goal_goal_type_meal_mealitem_progress"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="account",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="recent_users",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(
            assign_existing_recent_users_to_single_account,
            noop_reverse,
        ),
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(max_length=254),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                fields=("account", "email"),
                name="unique_recent_user_email_per_account",
            ),
        ),
    ]
