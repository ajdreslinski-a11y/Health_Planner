from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.utils import OperationalError, ProgrammingError
from django.shortcuts import get_object_or_404, redirect, render
from datetime import date

from .forms import AccountSignUpForm, FoodForm, MealItemForm, RecentUserForm
from .models import Food, Goal, Meal, MealItem, Progress, User


def register(request):
    if request.user.is_authenticated:
        return redirect("health:dashboard")

    if request.method == "POST":
        form = AccountSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("health:onboarding_goal")
    else:
        form = AccountSignUpForm()

    return render(request, "create_account.html", {"form": form})


@login_required
def onboarding_goal(request):
    if getattr(request.user, "onboarding_goal", None):
        return redirect("health:dashboard")

    choices = getattr(request.user, "ONBOARDING_GOAL_CHOICES", [])

    if request.method == "POST":
        goal = (request.POST.get("onboarding_goal") or "").strip()
        allowed = {k for (k, _label) in choices}
        if goal not in allowed:
            messages.error(request, "Please choose one option to continue.")
            return render(request, "health/onboarding_goal.html", {"choices": choices})

        request.user.onboarding_goal = goal
        request.user.save(update_fields=["onboarding_goal"])
        return redirect("health:dashboard")

    return render(request, "health/onboarding_goal.html", {"choices": choices})


@login_required
def dashboard(request):
    context = {
        "db_ready": True,
        "stats": {},
        "latest_foods": [],
        "latest_goals": [],
        "latest_meals": [],
        "latest_meal_items": [],
        "latest_progress": [],
        "latest_recent_users": [],
        "calorie_tracker": {},
    }

    try:
        context["stats"] = {
            "foods": Food.objects.count(),
            "goals": Goal.objects.filter(user=request.user).count(),
            "meals": Meal.objects.filter(user=request.user).count(),
            "meal_items": MealItem.objects.filter(meal__user=request.user).count(),
            "progress_entries": Progress.objects.filter(user=request.user).count(),
        }
        context["latest_foods"] = Food.objects.order_by("name")[:8]
        context["latest_goals"] = Goal.objects.filter(
            user=request.user
        ).order_by("-start_date")[:5]
        context["latest_meals"] = Meal.objects.filter(
            user=request.user
        ).order_by("-date", "-time")[:5]
        context["latest_meal_items"] = MealItem.objects.select_related(
            "meal", "food"
        ).filter(meal__user=request.user).order_by("-meal_item_id")[:6]
        context["latest_progress"] = Progress.objects.filter(
            user=request.user
        ).order_by("-date")[:5]

        context["latest_recent_users"] = User.objects.filter(
            account=request.user
        ).order_by("-created_at")[:5]
        
        # Calorie Tracker: Goal setting + Food logging + Daily remaining
        today = date.today()
        
        # Get the most recent active goal for the user
        active_goal = Goal.objects.filter(
            user=request.user
        ).order_by("-start_date").first()
        
        if active_goal:
            # Get today's total calories from meals
            today_meals = Meal.objects.filter(
                user=request.user,
                date=today
            ).aggregate(total=Sum('total_calories'))
            consumed = today_meals['total'] or 0
            
            # Calculate remaining
            remaining = active_goal.daily_calories - consumed
            
            # Determine status for color change (at 90% or more of limit)
            if consumed >= active_goal.daily_calories * 0.9:
                status = "warning"
            else:
                status = "normal"
            
            context["calorie_tracker"] = {
                "goal": active_goal.daily_calories,
                "consumed": consumed,
                "remaining": remaining,
                "status": status,
                "percentage": min(100, int((consumed / active_goal.daily_calories) * 100)) if active_goal.daily_calories > 0 else 0,
                "progress_style": f"width: {min(100, int((consumed / active_goal.daily_calories) * 100))}%" if active_goal.daily_calories > 0 else "width: 0%",
            }
    except (OperationalError, ProgrammingError):
        context["db_ready"] = False

    return render(request, "health/dashboard.html", context)


@login_required
def create_recent_user(request):
    if request.method == "POST":
        form = RecentUserForm(request.POST, account=request.user)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"{user.name} was added to Recent Users.")
            return redirect("health:dashboard")
    else:
        form = RecentUserForm(account=request.user)

    return render(
        request,
        "health/user_form.html",
        {
            "form": form,
            "form_title": "Add user info",
            "form_description": (
                "Enter the details from the user model, then we'll send you back "
                "to the dashboard and show the new name in Recent Users for this account."
            ),
            "submit_label": "Save user",
        },
    )


@login_required
def edit_recent_user(request, user_id):
    recent_user = get_object_or_404(User, pk=user_id, account=request.user)

    if request.method == "POST":
        form = RecentUserForm(
            request.POST, instance=recent_user, account=request.user
        )
        if form.is_valid():
            user = form.save()
            messages.success(request, f"{user.name}'s info was updated.")
            return redirect("health:dashboard")
    else:
        form = RecentUserForm(instance=recent_user, account=request.user)

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


@login_required
def create_goal(request):
    from .forms import GoalForm
    
    if request.method == "POST":
        form = GoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            # Associate the logged-in user as the user for this goal
            goal.user = request.user
            goal.save()
            messages.success(request, "Goal created successfully.")
            return redirect("health:dashboard")
    else:
        form = GoalForm()
    
    # Get user's current weight from the custom User model
    custom_user = User.objects.filter(account=request.user).first()
    user_weight = float(custom_user.weight) if custom_user and custom_user.weight else None
    
    # Calculate BMR using Mifflin-St Jeor formula (simplified)
    # BMR ≈ 10 * weight(kg) - assuming moderate activity
    if user_weight:
        weight_kg = user_weight * 0.453592  # convert lbs to kg
        base_bmr = int(10 * weight_kg)
    else:
        weight_kg = 70  # default weight in kg if not set
        base_bmr = 2000  # default if no weight set
    
    # Goal suggestions based on goal type and current weight
    goal_suggestions = {
        "lose": {
            "daily_calories": max(1200, base_bmr - 500),  # Create 500 cal deficit
            "protein": int(weight_kg * 1.6),  # ~1.6g per kg body weight
            "carbs": int((base_bmr - 500) * 0.3 / 4),  # 30% of calories from carbs
            "fat": int((base_bmr - 500) * 0.25 / 9),  # 25% of calories from fat
        },
        "gain": {
            "daily_calories": base_bmr + 500,  # Create 500 cal surplus
            "protein": int(weight_kg * 2.0),  # ~2g per kg for muscle gain
            "carbs": int((base_bmr + 500) * 0.45 / 4),  # 45% of calories from carbs
            "fat": int((base_bmr + 500) * 0.30 / 9),  # 30% of calories from fat
        },
        "maintain": {
            "daily_calories": base_bmr,
            "protein": int(weight_kg * 1.2),  # ~1.2g per kg
            "carbs": int(base_bmr * 0.35 / 4),  # 35% of calories from carbs
            "fat": int(base_bmr * 0.30 / 9),  # 30% of calories from fat
        },
        "muscle gain": {
            "daily_calories": base_bmr + 300,
            "protein": int(weight_kg * 1.8),  # ~1.8g per kg
            "carbs": int((base_bmr + 300) * 0.40 / 4),  # 40% of calories from carbs
            "fat": int((base_bmr + 300) * 0.25 / 9),  # 25% of calories from fat
        },
    }
    
    return render(
        request,
        "health/user_form.html",
        {
            "form": form,
            "form_title": "Create Health Goal",
            "form_description": "Select a goal type to see suggested values based on your weight, then customize your targets.",
            "submit_label": "Create Goal",
            "goal_suggestions": goal_suggestions,
            "user_weight": custom_user.weight if custom_user else None,
        },
    )


@login_required
def create_meal(request):
    from .forms import MealForm
    
    if request.method == "POST":
        form = MealForm(request.POST)
        if form.is_valid():
            meal = form.save(commit=False)
            # Associate the logged-in user as the user for this meal
            meal.user = request.user
            meal.save()
            messages.success(request, f"Meal '{meal.name}' created. Add foods to it.")
            return redirect("health:edit_meal_items", meal_id=meal.meal_id)
    else:
        form = MealForm()
    
    return render(
        request,
        "health/user_form.html",
        {
            "form": form,
            "form_title": "Log a Meal",
            "form_description": "Record a meal with date, time, and notes.",
            "submit_label": "Log Meal",
        },
    )


def _recalc_meal_totals(meal: Meal) -> None:
    totals = meal.meal_items.aggregate(
        calories=Sum("calories"),
        protein=Sum("protein"),
        carbs=Sum("carbs"),
        fat=Sum("fat"),
    )
    meal.total_calories = totals["calories"] or 0
    meal.total_protein = totals["protein"] or 0
    meal.total_carbs = totals["carbs"] or 0
    meal.total_fat = totals["fat"] or 0
    meal.save(
        update_fields=["total_calories", "total_protein", "total_carbs", "total_fat"]
    )


@login_required
def edit_meal_items(request, meal_id: int):
    meal = get_object_or_404(Meal, pk=meal_id, user=request.user)

    if request.method == "POST":
        form = MealItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.meal = meal
            item.save()
            _recalc_meal_totals(meal)
            messages.success(request, "Food added to meal.")
            return redirect("health:edit_meal_items", meal_id=meal.meal_id)
    else:
        form = MealItemForm()

    items = meal.meal_items.select_related("food").order_by("-meal_item_id")
    return render(
        request,
        "health/meal_items.html",
        {
            "meal": meal,
            "form": form,
            "items": items,
        },
    )


@login_required
def create_food(request):
    if request.method == "POST":
        form = FoodForm(request.POST)
        if form.is_valid():
            food = form.save()
            messages.success(request, f"Added '{food.name}' to the food database.")
            next_url = request.GET.get("next")
            if next_url:
                return redirect(next_url)
            return redirect("health:dashboard")
    else:
        form = FoodForm()

    return render(
        request,
        "health/user_form.html",
        {
            "form": form,
            "form_title": "Add a Food",
            "form_description": "Add a food (nutrition per 100g) so it can be reused in meals.",
            "submit_label": "Save food",
        },
    )
