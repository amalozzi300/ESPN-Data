from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, TemplateView

class Home(TemplateView):
    template_name = 'core/home.html'

class LoginUser(LoginView):
    template_name = 'core/login_user.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse('home')

class LogoutUser(LogoutView):
    next_page = reverse_lazy('home')

class RegisterUser(CreateView):
    form_class = UserCreationForm
    template_name = 'core/register_user.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, 'Account created successfully')
        return response