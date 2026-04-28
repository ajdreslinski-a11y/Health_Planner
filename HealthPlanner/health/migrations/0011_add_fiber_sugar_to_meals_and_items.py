from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("health", "0010_alter_food_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="meal",
            name="total_fiber",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=7),
        ),
        migrations.AddField(
            model_name="meal",
            name="total_sugar",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=7),
        ),
        migrations.AddField(
            model_name="mealitem",
            name="fiber",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=7),
        ),
        migrations.AddField(
            model_name="mealitem",
            name="sugar",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=7),
        ),
    ]
