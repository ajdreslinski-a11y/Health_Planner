from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    user_id = models.AutoField(primary_key=True)
    email = models.EmailField()
    password = models.CharField(max_length=128)
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField()
    height = models.DecimalField(max_digits=5, decimal_places=2, help_text="Height in ft")
    weight = models.DecimalField(max_digits=5, decimal_places=2, help_text="Weight in lbs")
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recent_users",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        db_table = 'users'
        constraints = [
            models.UniqueConstraint(
                fields=["account", "email"],
                name="unique_recent_user_email_per_account",
            )
        ]

    def __str__(self):
        return self.email


class Food(models.Model):
    """Food model with nutritional information per 100g"""
    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=200, blank=True, null=True)
    
    # Nutritional information per 100g
    calories_per_100g = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    protein_per_100g = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    carbs_per_100g = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    fat_per_100g = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    fiber_per_100g = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    sugar_per_100g = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    class Meta:
        db_table = 'foods'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.brand})" if self.brand else self.name

    def get_macros(self, grams):
        """Calculate macros for a given amount of grams (based on 100g standard)"""
        """Use this method to get macros for any amount of food based on the per 100g values"""
        factor = grams / 100
        return {
            'grams': grams,
            'calories': round(self.calories_per_100g * factor, 2),
            'protein': round(self.protein_per_100g * factor, 2),
            'carbs': round(self.carbs_per_100g * factor, 2),
            'fat': round(self.fat_per_100g * factor, 2),
            'fiber': round(self.fiber_per_100g * factor, 2),
            'sugar': round(self.sugar_per_100g * factor, 2),
        }

    def display_macros(self, grams=None):
        """Display macros for a given amount of grams"""
        if grams is None:
            grams = 100
        macros = self.get_macros(grams)
        return (
            f"{grams}g of {self.name}: "
            f"{macros['calories']} cal, "
            f"{macros['protein']}g protein, "
            f"{macros['carbs']}g carbs, "
            f"{macros['fat']}g fat, "
            f"{macros['fiber']}g fiber, "
            f"{macros['sugar']}g sugar"
        )


class Goal(models.Model):
    """Goal model for user health goals"""
    GOAL_TYPE_CHOICES = [
        ('lose', 'Lose Weight'),
        ('gain', 'Gain Weight'),
        ('maintain', 'Maintain Weight'),
        ('muscle gain', 'Muscle Gain'),
    ]

    goal_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goals')
    target_weight = models.DecimalField(max_digits=5, decimal_places=2, help_text="Target weight in lbs")
    daily_calories = models.PositiveIntegerField()
    protein = models.PositiveIntegerField(help_text="Protein in grams")
    carbs = models.PositiveIntegerField(help_text="Carbs in grams")
    fat = models.PositiveIntegerField(help_text="Fat in grams")
    goal_type = models.CharField(max_length=15, choices=GOAL_TYPE_CHOICES)
    start_date = models.DateField()

    class Meta:
        db_table = 'goals'
        ordering = ['-start_date']

    def __str__(self):
        return f"Goal {self.goal_id} - {self.user.name} - {self.get_goal_type_display()}"


class Meal(models.Model):
    """Meal model for tracking user meals"""
    MEAL_TYPE_CHOICES = [
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('snack', 'Snack'),
    ]

    meal_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meals')
    name = models.CharField(max_length=200, help_text="Name of the meal")
    meal_type = models.CharField(max_length=10, choices=MEAL_TYPE_CHOICES)
    date = models.DateField(help_text="Date of the meal")
    time = models.TimeField(help_text="Time of the meal")
    
    # Total nutritional info for the meal (calculated from foods)
    total_calories = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    total_protein = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    total_carbs = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    total_fat = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    
    notes = models.TextField(blank=True, null=True, help_text="Additional notes")

    class Meta:
        db_table = 'meals'
        ordering = ['-date', '-time']

    def __str__(self):
        return f"{self.name} ({self.get_meal_type_display()}) - {self.date}"


class MealItem(models.Model):
    """Through model to link meals with foods and track quantity"""
    meal_item_id = models.AutoField(primary_key=True)
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE, related_name='meal_items')
    food = models.ForeignKey(Food, on_delete=models.CASCADE, related_name='meal_items')
    quantity_grams = models.DecimalField(max_digits=7, decimal_places=2, help_text="Amount in grams")
    
    # Cached nutritional values (calculated at time of adding)
    calories = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    protein = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    carbs = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    fat = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    class Meta:
        db_table = 'meal_items'

    def save(self, *args, **kwargs):
        """Calculate nutritional values based on food and quantity"""
        if self.food and self.quantity_grams:
            macros = self.food.get_macros(float(self.quantity_grams))
            self.calories = macros['calories']
            self.protein = macros['protein']
            self.carbs = macros['carbs']
            self.fat = macros['fat']
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.food.name} - {self.quantity_grams}g"


class Progress(models.Model):
    """Progress model to track user weight and measurements over time"""
    progress_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress_records')
    date = models.DateField(help_text="Date of the progress entry")
    
    # Weight tracking
    weight = models.DecimalField(max_digits=5, decimal_places=2, help_text="Weight in lbs", null=True, blank=True)
    
    # Body measurements
    body_fat_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Body fat percentage")
    
    # Daily summary
    daily_calories_consumed = models.PositiveIntegerField(default=0)
    daily_protein_consumed = models.PositiveIntegerField(default=0)
    daily_carbs_consumed = models.PositiveIntegerField(default=0)
    daily_fat_consumed = models.PositiveIntegerField(default=0)
    

    class Meta:
        db_table = 'progress'
        ordering = ['-date']

    def __str__(self):
        return f"Progress - {self.user.name} - {self.date}"
