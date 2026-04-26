from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.utils import OperationalError, ProgrammingError
from django.shortcuts import get_object_or_404, redirect, render

from .forms import RecentUserForm
from .models import Food, Goal, Meal, MealItem, Progress, User


def register(request):
    if request.user.is_authenticated:
        return redirect("health:dashboard")

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("health:login")
    else:
        form = UserCreationForm()

    return render(request, "create_account.html", {"form": form})


@login_required
def dashboard(request):
    context = {
        "db_ready": True,
        "stats": {},
        "latest_users": [],
        "latest_foods": [],
        "latest_goals": [],
        "latest_meals": [],
        "latest_meal_items": [],
        "latest_progress": [],
    }

    try:
        context["stats"] = {
            "users": User.objects.count(),
            "foods": Food.objects.count(),
            "goals": Goal.objects.count(),
            "meals": Meal.objects.count(),
            "meal_items": MealItem.objects.count(),
            "progress_entries": Progress.objects.count(),
        }
        context["latest_users"] = User.objects.order_by("-created_at")[:5]
        context["latest_foods"] = Food.objects.order_by("name")[:8]
        context["latest_goals"] = Goal.objects.select_related("user").order_by("-start_date")[:5]
        context["latest_meals"] = Meal.objects.select_related("user").order_by("-date", "-time")[:5]
        context["latest_meal_items"] = MealItem.objects.select_related("meal", "food").order_by("-meal_item_id")[:6]
        context["latest_progress"] = Progress.objects.select_related("user").order_by("-date")[:5]
    except (OperationalError, ProgrammingError):
        context["db_ready"] = False

    return render(request, "health/dashboard.html", context)


@login_required
def create_recent_user(request):
    if request.method == "POST":
        form = RecentUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"{user.name} was added to Recent Users.")
            return redirect("health:dashboard")
    else:
        form = RecentUserForm()

    return render(
        request,
        "health/user_form.html",
        {
            "form": form,
            "form_title": "Add user info",
            "form_description": (
                "Enter the details from the user model, then we'll send you back "
                "to the dashboard and show the new name in Recent Users."
            ),
            "submit_label": "Save user",
        },
    )


@login_required
def edit_recent_user(request, user_id):
    recent_user = get_object_or_404(User, pk=user_id)

    if request.method == "POST":
        form = RecentUserForm(request.POST, instance=recent_user)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"{user.name}'s info was updated.")
            return redirect("health:dashboard")
    else:
        form = RecentUserForm(instance=recent_user)

    return render(
        request,
        "health/user_form.html",
        {
            "form": form,
            "form_title": f"Edit {recent_user.name}",
            "form_description": (
                "Update this user's name, age, height, weight, or email, then save "
                "to refresh what appears in Recent Users."
            ),
            "submit_label": "Save changes",
        },
    )
