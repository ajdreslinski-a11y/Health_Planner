from django import forms

from .models import User


class RecentUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["name", "email", "age", "height", "weight"]
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
        }

    def save(self, commit=True):
        user = super().save(commit=False)

        if not user.password:
            user.set_unusable_password()

        if commit:
            user.save()

        return user
