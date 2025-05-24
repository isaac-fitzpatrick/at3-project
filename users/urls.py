from django.urls import path
from . import views

urlpatterns = [
    path("", views.select_role, name="home"),  # <-- changed home view to root URL
    path("user/", views.user, name="user"),    # <-- Moved user view to /user/
    path("login", views.login_view, name="login"),
    path("teacher_login", views.teacher_login_view, name="teacher_login"),
    path("logout", views.logout_view, name="logout"),
    path('register/', views.register, name='register'),
    path('top-up/', views.top_up, name='top_up')
]