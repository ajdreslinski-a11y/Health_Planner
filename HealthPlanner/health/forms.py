from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Food, Meal, MealItem, User


class AccountSignUpForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("password1", "password2"):
            if name in self.fields:
                self.fields[name].widget.attrs.setdefault("class", "form-control")
        if "sex" in self.fields:
            self.fields["sex"].required = False
            self.fields["sex"].choices = [
                ("", "(optional improves calorie estimates)"),
            ] + list(get_user_model().SEX_CHOICES)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ["email", "name", "age", "height", "weight", "sex"]
        widgets = {
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "Enter email address"}
            ),
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter full name"}
            ),
            "age": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Enter age", "min": 0}
            ),
            "height": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Height in feet",
                    "step": "0.01",
                    "min": 0,
                }
            ),
            "weight": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Weight in pounds",
                    "step": "0.01",
                    "min": 0,
                }
            ),
            "sex": forms.Select(attrs={"class": "form-select"}),
        }


class RecentUserForm(forms.ModelForm):
    def __init__(self, *args, account=None, **kwargs):
        super().__init__(*args, **kwargs)
        if account is not None:
            self.instance.account = account
        if "sex" in self.fields:
            self.fields["sex"].required = False
            self.fields["sex"].choices = [
                ("", "(optional)"),
            ] + list(User.SEX_CHOICES)

    class Meta:
        model = User
        fields = ["name", "email", "age", "height", "weight", "sex"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter full name"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "Enter email address"}
            ),
            "age": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Enter age", "min": 0}
            ),
            "height": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Height in feet",
                    "step": "0.01",
                    "min": 0,
                }
            ),
            "weight": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Weight in pounds",
                    "step": "0.01",
                    "min": 0,
                }
            ),
            "sex": forms.Select(attrs={"class": "form-select"}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)

        if not user.password:
            user.set_unusable_password()

        if commit:
            user.save()
        return user


class GoalForm(forms.ModelForm):
    class Meta:
        from .models import Goal
        model = Goal
        fields = ["goal_type", "target_weight", "daily_calories", "protein", "carbs", "fat", "start_date"]
        widgets = {
            "goal_type": forms.Select(attrs={"class": "form-select"}),
            "target_weight": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Target weight in lbs", "step": "0.01", "min": 0}
            ),
            "daily_calories": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Daily calorie target", "min": 0}
            ),
            "protein": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Protein in grams", "min": 0}
            ),
            "carbs": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Carbs in grams", "min": 0}
            ),
            "fat": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Fat in grams", "min": 0}
            ),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Reorder fields to show goal_type first
        self.fields_order = ["goal_type", "target_weight", "daily_calories", "protein", "carbs", "fat", "start_date"]


class MealForm(forms.ModelForm):
    class Meta:
        model = Meal
        fields = ["name", "meal_type", "date", "time", "notes"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Meal name"}
            ),
            "meal_type": forms.Select(attrs={"class": "form-select"}),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "time": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "notes": forms.Textarea(
                attrs={"class": "form-control", "placeholder": "Additional notes", "rows": 3}
            ),
        }


class MealItemForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["food"].queryset = Food.objects.order_by("name")

    class Meta:
        model = MealItem
        fields = ["food", "quantity_grams"]
        widgets = {
            "food": forms.Select(attrs={"class": "form-select"}),
            "quantity_grams": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Amount in grams", "step": "0.01", "min": 0}
            ),
        }


class FoodForm(forms.ModelForm):
    class Meta:
        model = Food
        fields = [
            "name",
            "brand",
            "calories_per_100g",
            "protein_per_100g",
            "carbs_per_100g",
            "fat_per_100g",
            "fiber_per_100g",
            "sugar_per_100g",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. Chicken breast"}
            ),
            "brand": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Optional brand"}
            ),
            "calories_per_100g": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": 0}
            ),
            "protein_per_100g": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": 0}
            ),
            "carbs_per_100g": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": 0}
            ),
            "fat_per_100g": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": 0}
            ),
            "fiber_per_100g": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": 0}
            ),
            "sugar_per_100g": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": 0}
            ),
        }
