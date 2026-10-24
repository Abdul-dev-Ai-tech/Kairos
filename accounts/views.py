from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.auth.views import PasswordResetView
from django.conf import settings
from django.db import IntegrityError
from django.shortcuts import render, redirect
from catalog.models import Wishlist, Product
from orders.services import get_cart
from .forms import EmailLoginForm, ProfileForm, RegisterForm
from core.models import StoreSettings

class BrandedPasswordResetView(PasswordResetView):
    def form_valid(self, form):
        self.extra_email_context = {'store': StoreSettings.load(), 'site_url': settings.SITE_URL}
        return super().form_valid(form)

def merge_saved(request):
    get_cart(request, create=False)
    for pk in request.session.pop('wishlist', []):
        if Product.objects.filter(pk=pk).exists():
            Wishlist.objects.get_or_create(user=request.user, product_id=pk)

class CustomerLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = EmailLoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        merge_saved(self.request)
        return response

def register(request):
    if request.user.is_authenticated:
        return redirect('accounts:profile')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            user = form.save()
        except IntegrityError:
            form.add_error('email', 'An account with this email already exists.')
        else:
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            merge_saved(request)
            messages.success(request, 'Welcome to KAIROS STORE. Your account is ready.')
            return redirect('accounts:profile')
    return render(request, 'accounts/register.html', {'form': form})

@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Your profile has been updated.')
        return redirect('accounts:profile')
    return render(request, 'accounts/profile.html', {'form': form, 'orders': request.user.orders.all()[:5]})
