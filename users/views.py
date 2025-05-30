from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegistrationForm
from .forms import BalanceTopupForm
import requests
from django.conf import settings
import os

def register(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your account has been created! You can now log in.")
            return redirect('users:login')
    else:
        form = UserRegistrationForm()
    return render(request, 'users/register.html', {'form': form})

def select_role(request):
    if request.method == "POST":
        role = request.POST.get('role-choice')
        if role == 'teacher':
            return render(request, 'users/teacher_login.html')
        elif role == 'student':
            return render(request, 'users/login.html')
    return render(request, 'users/home.html')

@login_required(login_url='users:login')
def user(request):
    profile = request.user.profile # requests user info
    return render(request, "users/user.html", {
        'user': request.user, # gets user from user info
    })

def teacher_login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        recaptcha_response = request.POST.get("recaptcha-token")
        # Verify reCAPTCHA
        data = {
            'secret': settings.RECAPTCHA_SECRET_KEY,
            'response': recaptcha_response,
            'remoteip': request.META.get('REMOTE_ADDR'),
        }
        recaptcha_verification = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data=data
        )
        result = recaptcha_verification.json()
        if result.get("success"):
            messages.error(request, "reCAPTCHA validation failed. Please try again.")
            return redirect("users:teacher_login")
        # Authenticate user using the teacher DB backend
        user = authenticate(request, username=username, password=password, backend='users.backends.TeacherDBBackend')
        if user is not None:
            login(request, user, backend='users.backends.TeacherDBBackend')
            next_url = request.GET.get('next', reverse("users:user"))
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, "users/teacher_login.html")

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        recaptcha_response = request.POST.get("recaptcha-token")  # Updated
        # Verify reCAPTCHA
        data = {
            'secret': settings.RECAPTCHA_SECRET_KEY,
            'response': recaptcha_response,
            'remoteip': request.META.get('REMOTE_ADDR'),
        }
        recaptcha_verification = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data=data
        )
        result = recaptcha_verification.json()
        # Check reCAPTCHA response
        if result.get("success"):
            messages.error(request, "reCAPTCHA validation failed. Please try again.")
            return redirect("users:login")  # Redirect back to the login page
        # Authenticate user if reCAPTCHA is valid
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Redirect to the next URL if provided, else default to user profile
            next_url = request.GET.get('next', reverse("users:user"))  # Simplified fallback
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, "users/login.html")

def logout_view(request):
    logout(request)
    messages.success(request, "Successfully logged out.")
    return redirect('users:login')

@login_required
def user_view(request):
    profile = request.user.profile  # gets user's profile
    permissions = request.user.permissions
    return render(request, 'users/user.html', {'balance': profile.balance})

@login_required
def top_up(request):
    if request.method == "POST": # makes sure its a post request
        profile = request.user.profile 
        form = BalanceTopupForm(request.POST)
        if form.is_valid(): # if BalanceTopupForm returns valid it means it follows all criteria (2 dec places, max 5 digits, 0.01 minimum)
            amount = form.cleaned_data['amount'] # sets amount to the corrected value provided by BalanceTopupForm
            profile.balance += amount # adds the top-up amount to the existing balance
            profile.save() # saves the profile's balance
            messages.success(request, f"Your balance has been topped up by ${amount}.") # success message for user
            return redirect('users:user') # redirects to users/
        else:
            print(form.errors)
            return render(request, 'users/top_up.html', {'form': form})
    else:
        form = BalanceTopupForm()
        return render(request, 'users/top_up.html', {'form': form})