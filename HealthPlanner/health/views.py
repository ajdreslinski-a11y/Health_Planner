from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render


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
    return render(request, "health/dashboard.html")
