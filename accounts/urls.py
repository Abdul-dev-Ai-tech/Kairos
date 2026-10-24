from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth
from . import views
app_name = 'accounts'
urlpatterns = [
    path('login/', views.CustomerLoginView.as_view(), name='login'),
    path('register/', views.register, name='register'),
    path('logout/', auth.LogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('password-reset/', views.BrandedPasswordResetView.as_view(
        template_name='registration/password_form.html', email_template_name='registration/password_reset_email.txt',
        html_email_template_name='registration/password_reset_email.html', subject_template_name='registration/password_reset_subject.txt',
        success_url=reverse_lazy('accounts:password_reset_done')), name='password_reset'),
    path('password-reset/sent/', auth.PasswordResetDoneView.as_view(template_name='registration/password_sent.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth.PasswordResetConfirmView.as_view(template_name='registration/password_form.html', success_url=reverse_lazy('accounts:password_reset_complete')), name='password_reset_confirm'),
    path('reset/complete/', auth.PasswordResetCompleteView.as_view(template_name='registration/password_complete.html'), name='password_reset_complete'),
    path('password-change/', auth.PasswordChangeView.as_view(template_name='registration/password_form.html', success_url=reverse_lazy('accounts:password_change_done')), name='password_change'),
    path('password-change/done/', auth.PasswordChangeDoneView.as_view(template_name='registration/password_complete.html'), name='password_change_done'),
]
