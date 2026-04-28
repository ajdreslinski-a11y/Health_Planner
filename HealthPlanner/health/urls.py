from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "health"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("onboarding/goal/", views.onboarding_goal, name="onboarding_goal"),
    path("foods/new/", views.create_food, name="create_food"),
    path("users/new/", views.create_recent_user, name="create_recent_user"),
    path("users/<int:user_id>/edit/", views.edit_recent_user, name="edit_recent_user"),
    path("goals/new/", views.create_goal, name="create_goal"),
    path("progress/new/", views.create_progress, name="create_progress"),
    path("progress/<int:progress_id>/edit/", views.edit_progress, name="edit_progress"),
    path("meals/new/", views.create_meal, name="create_meal"),
    path("meals/<int:meal_id>/edit/", views.edit_meal, name="edit_meal"),
    path("meals/<int:meal_id>/delete/", views.delete_meal, name="delete_meal"),
    path("meals/<int:meal_id>/items/", views.edit_meal_items, name="edit_meal_items"),
    path("meal-items/<int:meal_item_id>/edit/", views.edit_meal_item, name="edit_meal_item"),
    path("meal-items/<int:meal_item_id>/delete/", views.delete_meal_item, name="delete_meal_item"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
]
