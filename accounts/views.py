from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomUserChangeForm, ProfileUpdateForm
from django.contrib.auth.forms import AuthenticationForm

def register_view(request):
    if request.user.is_authenticated:
        return redirect('store:home')
        
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Hesabınız başarıyla oluşturuldu. CoreLogic Store'a hoş geldiniz!")
            return redirect('store:home')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('store:home')
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Hoş geldiniz, {user.username}!')
            next_url = request.GET.get('next', 'store:home')
            return redirect(next_url)
    else:
        form = AuthenticationForm()
        
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, 'Başarıyla çıkış yaptınız.')
    return redirect('store:home')

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil bilgileriniz güncellendi.')
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)
        
    orders = request.user.orders.all().order_by('-created_at')
    
    return render(request, 'accounts/profile.html', {
        'form': form,
        'orders': orders
    })
