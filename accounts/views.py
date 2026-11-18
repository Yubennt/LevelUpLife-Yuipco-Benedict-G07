from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from gamification.services import level_progress

from .forms import LoginForm, ProfileForm, RegisterForm


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST if request.method == "POST" else None)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Account created! Log in to start levelling up.")
            return redirect("login")
        messages.error(request, "Please fix the errors below and try again.")
    return render(request, "registration/register.html", {"form": form})


class UserLoginView(LoginView):
    form_class = LoginForm
    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Welcome back, {form.get_user().display_name}!")
        return response


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("login")


class UserPasswordChangeView(SuccessMessageMixin, PasswordChangeView):
    template_name = "registration/password_change_form.html"
    success_url = reverse_lazy("profile")
    success_message = "Your password was changed."


@login_required
def profile(request):
    """Always the logged-in user's own profile (no user id in the URL, BR-06)."""
    return render(request, "accounts/profile.html", {"profile_user": request.user, "progress": level_progress(request.user)})


@login_required
def profile_edit(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
    else:
        form = ProfileForm(instance=request.user)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("profile")
        messages.error(request, "Please fix the errors below.")
    return render(request, "accounts/profile_edit.html", {"form": form})
