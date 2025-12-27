from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView

class Home(TemplateView):
    template_name = 'core/home.html'

class Login(LoginView):
    template_name = 'core/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse('home')

class Logout(LogoutView):
    next_page = reverse_lazy('home')