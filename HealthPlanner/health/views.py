from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.utils import OperationalError, ProgrammingError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    AccountSignUpForm,
    FoodForm,
    MealForm,
    MealItemForm,
    ProgressForm,
    RecentUserForm,
)
from .models import Food, Goal, Meal, MealItem, Progress, User
from .nutrition import build_goal_suggestions, compute_maintenance, dashboard_copy


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
    if request.method == "POST" and request.POST.get("action") == "maintenance":
        try:
            w = float(request.POST.get("calc_weight_lb") or 0)
            h_ft = float(request.POST.get("calc_height_ft") or 0)
            age = int(request.POST.get("calc_age") or 0)
            sex_raw = (request.POST.get("calc_sex") or "").strip()
            sex = sex_raw if sex_raw in ("M", "F") else None
            activity = request.POST.get("calc_activity") or "moderate"
            if w > 0 and h_ft > 0 and age > 0:
                result = compute_maintenance(
                    weight_lbs=w,
                    height_ft=h_ft,
                    age=age,
                    sex=sex,
                    activity_level=activity,
                )
                request.session["maintenance_result"] = result
                messages.success(
                    request,
                    "Estimated maintenance calories are ready below.",
                )
                return redirect("health:dashboard")
            messages.error(
                request,
                "Weight, height (ft), and age must be positive numbers.",
            )
        except (TypeError, ValueError):
            messages.error(
                request,
                "Could not parse the calculator inputs. Use numbers only.",
            )

    maintenance_snapshot = request.session.pop("maintenance_result", None)

    context = {
        "db_ready": True,
        "stats": {},
        "latest_foods": [],
        "latest_goals": [],
        "latest_meals": [],
        "latest_progress": [],
        "latest_progress_rows": [],
        "latest_recent_users": [],
        "calorie_tracker": {},
        "macro_tracker": {},
        "maintenance_result": maintenance_snapshot,
        "coach_tips": [],
        "coach_bmi": None,
        "coach_tdee_estimate": None,
    }

    try:
        context["stats"] = {
            "foods": Food.objects.count(),
            "goals": Goal.objects.filter(user=request.user).count(),
            "meals": Meal.objects.filter(user=request.user).count(),
            "progress_entries": Progress.objects.filter(user=request.user).count(),
        }
        context["latest_foods"] = Food.objects.order_by("name")[:8]
        context["latest_goals"] = Goal.objects.filter(
            user=request.user
        ).order_by("-start_date")[:5]
        context["latest_meals"] = Meal.objects.filter(
            user=request.user
        ).order_by("-date", "-time")[:5]
        latest_progress = list(
            Progress.objects.filter(
                user=request.user
            ).order_by("-date")[:5]
        )
        context["latest_progress"] = latest_progress
        context["latest_progress_rows"] = []
        for entry in latest_progress:
            meal_totals = Meal.objects.filter(
                user=request.user, date=entry.date
            ).aggregate(
                calories=Sum("total_calories"),
                protein=Sum("total_protein"),
                carbs=Sum("total_carbs"),
                fat=Sum("total_fat"),
            )
            goal_for_day = Goal.objects.filter(
                user=request.user, start_date__lte=entry.date
            ).order_by("-start_date").first()

            calories_val = int(
                round(
                    float(
                        entry.daily_calories_consumed
                        or meal_totals["calories"]
                        or 0
                    )
                )
            )
            protein_val = int(
                round(
                    float(
                        entry.daily_protein_consumed
                        or meal_totals["protein"]
                        or 0
                    )
                )
            )
            carbs_val = int(
                round(
                    float(
                        entry.daily_carbs_consumed
                        or meal_totals["carbs"]
                        or 0
                    )
                )
            )
            fat_val = int(
                round(
                    float(
                        entry.daily_fat_consumed
                        or meal_totals["fat"]
                        or 0
                    )
                )
            )

            goal_units = goal_for_day.daily_calories if goal_for_day else None
            delta_units = calories_val - goal_units if goal_units else None
            pct_of_goal = (
                int(round((calories_val / float(goal_units)) * 100))
                if goal_units and goal_units > 0
                else None
            )

            context["latest_progress_rows"].append(
                {
                    "entry": entry,
                    "calories": calories_val,
                    "protein": protein_val,
                    "carbs": carbs_val,
                    "fat": fat_val,
                    "goal_units": goal_units,
                    "delta_units": delta_units,
                    "abs_delta_units": abs(delta_units) if delta_units is not None else None,
                    "pct_of_goal": pct_of_goal,
                }
            )

        context["latest_recent_users"] = User.objects.filter(
            account=request.user
        ).order_by("-created_at")[:5]

        u = request.user
        coach_tips, coach_bmi, coach_tdee = dashboard_copy(
            weight_lbs=float(u.weight) if u.weight is not None else None,
            height_ft=float(u.height) if u.height is not None else None,
            age=u.age,
            sex=getattr(u, "sex", None),
            onboarding_goal=getattr(u, "onboarding_goal", None),
        )
        context["coach_tips"] = coach_tips
        context["coach_bmi"] = coach_bmi
        context["coach_tdee_estimate"] = coach_tdee
        
        # Calorie Tracker: Goal setting + Food logging + Daily remaining
        today = timezone.localdate()
        
        # Get the most recent active goal for the user
        active_goal = Goal.objects.filter(
            user=request.user
        ).order_by("-start_date").first()
        
        if active_goal:
            today_meals = Meal.objects.filter(
                user=request.user,
                date=today
            ).aggregate(
                calories=Sum("total_calories"),
                protein=Sum("total_protein"),
                carbs=Sum("total_carbs"),
                fat=Sum("total_fat"),
            )
            raw_total = today_meals["calories"]
            consumed_units = round(float(raw_total or 0))
            daily_goal_units = active_goal.daily_calories
            
            ratio_pct = (
                (consumed_units / float(daily_goal_units)) * 100 if daily_goal_units > 0 else 0
            )
            bar_pct = max(0, min(100, int(round(ratio_pct))))
            pct_label = max(0, int(round(ratio_pct)))
            overflow_units = consumed_units - daily_goal_units
            
            consumed = consumed_units
            over_goal = daily_goal_units > 0 and overflow_units > 0

            if over_goal:
                status = "over"
            elif daily_goal_units > 0 and consumed_units >= int(
                daily_goal_units * 0.9
            ):
                status = "warning"
            else:
                status = "normal"

            remaining_int = max(daily_goal_units - consumed_units, 0)

            context["calorie_tracker"] = {
                "goal": daily_goal_units,
                "consumed": consumed,
                "remaining": remaining_int,
                "pct_label": pct_label,
                "over_goal": over_goal,
                "overflow_units": max(overflow_units, 0) if over_goal else 0,
                "status": status,
                "percentage": bar_pct,
                "progress_style": f"width: {bar_pct}%",
            }

            protein_g = int(round(float(today_meals["protein"] or 0)))
            carbs_g = int(round(float(today_meals["carbs"] or 0)))
            fat_g = int(round(float(today_meals["fat"] or 0)))
            total_g = max(protein_g + carbs_g + fat_g, 0)
            if total_g > 0:
                protein_pct = int(round((protein_g / float(total_g)) * 100))
                carbs_pct = int(round((carbs_g / float(total_g)) * 100))
                fat_pct = max(0, 100 - protein_pct - carbs_pct)
            else:
                protein_pct = carbs_pct = fat_pct = 0

            context["macro_tracker"] = {
                "protein_g": protein_g,
                "carbs_g": carbs_g,
                "fat_g": fat_g,
                "protein_pct": protein_pct,
                "carbs_pct": carbs_pct,
                "fat_pct": fat_pct,
                "total_g": total_g,
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
            goal.user = request.user
            goal.save()
            messages.success(request, "Goal created successfully.")
            return redirect("health:dashboard")
    else:
        form = GoalForm()
    
    u = request.user
    goal_descriptions, intro_blurbs = build_goal_suggestions(
        weight_lbs=u.weight,
        height_ft=u.height,
        age=u.age,
        sex=getattr(u, "sex", None),
        onboarding_goal=getattr(u, "onboarding_goal", None),
        activity_default="moderate",
    )

    trimmed = {}
    for key, vals in goal_descriptions.items():
        trimmed[key] = {
            "daily_calories": vals["daily_calories"],
            "protein": vals["protein"],
            "carbs": vals["carbs"],
            "fat": vals["fat"],
            "note": vals.get("note", ""),
        }
    
    return render(
        request,
        "health/user_form.html",
        {
            "form": form,
            "form_title": "Create Health Goal",
            "form_description": "Select a goal type to review macro targets tied to your height, weight, age, onboarding intent, then customize anything you need.",
            "submit_label": "Create Goal",
            "goal_suggestions": trimmed,
            "goal_intro_blurbs": intro_blurbs,
            "user_weight": u.weight,
        },
    )


@login_required
def create_progress(request):
    if request.method == "POST":
        form = ProgressForm(request.POST)
        if form.is_valid():
            progress = form.save(commit=False)
            progress.user = request.user
            progress.save()
            messages.success(request, "Progress entry logged.")
            return redirect("health:dashboard")
    else:
        form = ProgressForm(initial={"date": timezone.localdate()})

    return render(
        request,
        "health/user_form.html",
        {
            "form": form,
            "form_title": "Log Daily Progress",
            "form_description": (
                "Track weight, optional body-fat percentage, and your daily macro totals."
            ),
            "submit_label": "Save progress",
        },
    )


@login_required
def edit_progress(request, progress_id: int):
    progress_entry = get_object_or_404(Progress, pk=progress_id, user=request.user)

    if request.method == "POST":
        form = ProgressForm(request.POST, instance=progress_entry)
        if form.is_valid():
            form.save()
            messages.success(request, "Progress entry updated.")
            return redirect("health:dashboard")
    else:
        form = ProgressForm(instance=progress_entry)

    return render(
        request,
        "health/user_form.html",
        {
            "form": form,
            "form_title": f"Edit Progress: {progress_entry.date}",
            "form_description": "Update this daily progress record, then save.",
            "submit_label": "Save changes",
        },
    )


@login_required
def create_meal(request):
    # Get all foods for the library selection
    foods_payload = list(
        Food.objects.order_by("name").values(
            "id",
            "name",
            "brand",
            "calories_per_100g",
            "protein_per_100g",
            "carbs_per_100g",
            "fat_per_100g",
            "fiber_per_100g",
            "sugar_per_100g",
        )
    )
    
    if request.method == "POST":
        form = MealForm(request.POST)
        if form.is_valid():
            meal = form.save(commit=False)
            # Associate the logged-in user as the user for this meal
            meal.user = request.user
            meal.save()
            messages.success(request, f"Meal '{meal.name}' logged.")
            return redirect("health:dashboard")
    else:
        form = MealForm()
    
    return render(
        request,
        "health/user_form.html",
        {
            "form": form,
            "form_title": "Log a Meal",
            "form_description": "Enter the meal's macros directly (no foods needed).",
            "submit_label": "Log Meal",
            "foods_payload": foods_payload,
        },
    )


@login_required
def edit_meal(request, meal_id: int):
    meal = get_object_or_404(Meal, pk=meal_id, user=request.user)

    if request.method == "POST":
        form = MealForm(request.POST, instance=meal)
        if form.is_valid():
            updated_meal = form.save()
            messages.success(request, f"Meal '{updated_meal.name}' was updated.")
            return redirect("health:dashboard")
    else:
        form = MealForm(instance=meal)

    return render(
        request,
        "health/user_form.html",
        {
            "form": form,
            "form_title": f"Edit Meal: {meal.name}",
            "form_description": "Update meal details, then save to refresh your dashboard list.",
            "submit_label": "Save meal",
        },
    )


@login_required
def delete_meal(request, meal_id: int):
    meal = get_object_or_404(Meal, pk=meal_id, user=request.user)

    if request.method != "POST":
        return redirect("health:dashboard")

    meal_name = meal.name
    meal.delete()
    messages.success(request, f"Meal '{meal_name}' was deleted.")
    return redirect("health:dashboard")


@login_required
def edit_meal_item(request, meal_item_id: int):
    meal_item = get_object_or_404(
        MealItem.objects.select_related("meal", "food"),
        pk=meal_item_id,
        meal__user=request.user,
    )

    if request.method == "POST":
        form = MealItemForm(request.POST, instance=meal_item)
        if form.is_valid():
            updated_item = form.save()
            _recalc_meal_totals(updated_item.meal)
            messages.success(request, "Meal item was updated.")
            return redirect("health:dashboard")
    else:
        form = MealItemForm(instance=meal_item)

    return render(
        request,
        "health/user_form.html",
        {
            "form": form,
            "form_title": f"Edit Meal Item: {meal_item.food.name}",
            "form_description": (
                f"Update this item in {meal_item.meal.name}, then save to refresh your dashboard list."
            ),
            "submit_label": "Save meal item",
        },
    )


@login_required
def delete_meal_item(request, meal_item_id: int):
    meal_item = get_object_or_404(
        MealItem.objects.select_related("meal", "food"),
        pk=meal_item_id,
        meal__user=request.user,
    )

    if request.method != "POST":
        return redirect("health:dashboard")

    meal = meal_item.meal
    meal_item.delete()
    _recalc_meal_totals(meal)
    messages.success(request, "Meal item was deleted.")
    return redirect("health:dashboard")


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
    foods_payload = list(
        Food.objects.order_by("name").values(
            "id",
            "name",
            "brand",
            "calories_per_100g",
            "protein_per_100g",
            "carbs_per_100g",
            "fat_per_100g",
            "fiber_per_100g",
            "sugar_per_100g",
        )
    )
    return render(
        request,
        "health/meal_items.html",
        {
            "meal": meal,
            "form": form,
            "items": items,
            "foods_payload": foods_payload,
        },
    )


@login_required
def create_food(request):
    # Get all foods for the library selection
    foods_payload = list(
        Food.objects.order_by("name").values(
            "id",
            "name",
            "brand",
            "calories_per_100g",
            "protein_per_100g",
            "carbs_per_100g",
            "fat_per_100g",
            "fiber_per_100g",
            "sugar_per_100g",
        )
    )
    
    if request.method == "POST":
        form = FoodForm(request.POST)
        if form.is_valid():
            food = form.save()
            messages.success(request, f"Added '{food.name}' to the food database.")
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
            "foods_payload": foods_payload,
        },
    )
