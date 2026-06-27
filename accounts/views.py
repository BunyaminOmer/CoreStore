import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import CustomUserCreationForm, EmailTwoFactorForm, ProfileUpdateForm
from .models import CustomUser, EmailTwoFactorCode


SESSION_2FA_USER_ID = 'email_2fa_user_id'
SESSION_2FA_PURPOSE = 'email_2fa_purpose'
SESSION_2FA_NEXT = 'email_2fa_next'
SESSION_2FA_LAST_SENT = 'email_2fa_last_sent'


def get_safe_next_url(request, fallback='store:home'):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return reverse(fallback)


def hash_2fa_code(code):
    return hashlib.sha256(f'{settings.SECRET_KEY}:{code}'.encode('utf-8')).hexdigest()


def create_email_2fa_code(user, purpose):
    code = ''.join(str(secrets.randbelow(10)) for _ in range(6))
    EmailTwoFactorCode.objects.filter(
        user=user,
        purpose=purpose,
        used_at__isnull=True,
    ).update(used_at=timezone.now())

    token = EmailTwoFactorCode.objects.create(
        user=user,
        purpose=purpose,
        code_hash=hash_2fa_code(code),
        sent_to=user.email,
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    return token, code


def send_email_2fa_code(request, user, purpose):
    last_sent = request.session.get(SESSION_2FA_LAST_SENT)
    if last_sent:
        elapsed = timezone.now().timestamp() - float(last_sent)
        if elapsed < 60:
            return False

    token, code = create_email_2fa_code(user, purpose)
    subject = 'CoreLogic Store doğrulama kodunuz'
    message = (
        f'Merhaba {user.get_full_name() or user.username},\n\n'
        f'CoreLogic Store doğrulama kodunuz: {code}\n'
        'Bu kod 10 dakika geçerlidir.\n\n'
        'Bu işlemi siz başlatmadıysanız bu e-postayı yok sayabilirsiniz.'
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [token.sent_to],
        fail_silently=False,
    )
    request.session[SESSION_2FA_LAST_SENT] = str(timezone.now().timestamp())
    if settings.EMAIL_2FA_SHOW_DEBUG_CODE:
        messages.info(request, f'Geliştirme doğrulama kodu: {code}')
    return True


def start_email_2fa(request, user, purpose, next_url):
    request.session[SESSION_2FA_USER_ID] = user.pk
    request.session[SESSION_2FA_PURPOSE] = purpose
    request.session[SESSION_2FA_NEXT] = next_url
    request.session.pop(SESSION_2FA_LAST_SENT, None)
    send_email_2fa_code(request, user, purpose)
    return redirect('accounts:verify_email_2fa')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('store:home')
        
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.info(request, 'Hesabınızı tamamlamak için e-postanıza gönderilen kodu girin.')
            return start_email_2fa(request, user, EmailTwoFactorCode.PURPOSE_REGISTER, reverse('store:home'))
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
            next_url = get_safe_next_url(request)
            if user.email_2fa_enabled:
                messages.info(request, 'Güvenli giriş için e-postanıza doğrulama kodu gönderdik.')
                return start_email_2fa(request, user, EmailTwoFactorCode.PURPOSE_LOGIN, next_url)
            login(request, user)
            messages.success(request, f'Hoş geldiniz, {user.username}!')
            return redirect(next_url)
    else:
        form = AuthenticationForm()
        
    return render(request, 'accounts/login.html', {
        'form': form,
        'next': request.GET.get('next', ''),
    })


def verify_email_2fa_view(request):
    if request.user.is_authenticated:
        return redirect('store:home')

    user_id = request.session.get(SESSION_2FA_USER_ID)
    purpose = request.session.get(SESSION_2FA_PURPOSE)
    if not user_id or purpose not in dict(EmailTwoFactorCode.PURPOSE_CHOICES):
        messages.warning(request, 'Doğrulama oturumu bulunamadı. Lütfen tekrar giriş yapın.')
        return redirect('accounts:login')

    user = get_object_or_404(CustomUser, pk=user_id)
    token = EmailTwoFactorCode.objects.filter(
        user=user,
        purpose=purpose,
        used_at__isnull=True,
    ).order_by('-created_at').first()

    if request.method == 'POST':
        form = EmailTwoFactorForm(request.POST)
        if form.is_valid():
            if not token or not token.is_usable:
                messages.error(request, 'Kodun süresi doldu. Lütfen yeni kod isteyin.')
                return redirect('accounts:verify_email_2fa')

            token.attempts += 1
            if token.code_hash == hash_2fa_code(form.cleaned_data['code']):
                token.used_at = timezone.now()
                token.save(update_fields=['attempts', 'used_at'])
                if not user.email_verified_at:
                    user.email_verified_at = timezone.now()
                    user.save(update_fields=['email_verified_at'])

                next_url = request.session.get(SESSION_2FA_NEXT) or reverse('store:home')
                for key in (SESSION_2FA_USER_ID, SESSION_2FA_PURPOSE, SESSION_2FA_NEXT, SESSION_2FA_LAST_SENT):
                    request.session.pop(key, None)
                login(request, user)
                messages.success(request, f'Hoş geldiniz, {user.username}!')
                return redirect(next_url)

            token.save(update_fields=['attempts'])
            messages.error(request, 'Doğrulama kodu hatalı.')
    else:
        form = EmailTwoFactorForm()

    return render(request, 'accounts/verify_email_2fa.html', {
        'form': form,
        'email': user.email,
        'purpose': purpose,
    })


def resend_email_2fa_view(request):
    user_id = request.session.get(SESSION_2FA_USER_ID)
    purpose = request.session.get(SESSION_2FA_PURPOSE)
    if not user_id or purpose not in dict(EmailTwoFactorCode.PURPOSE_CHOICES):
        messages.warning(request, 'Doğrulama oturumu bulunamadı. Lütfen tekrar giriş yapın.')
        return redirect('accounts:login')

    user = get_object_or_404(CustomUser, pk=user_id)
    if send_email_2fa_code(request, user, purpose):
        messages.success(request, 'Yeni doğrulama kodu e-postanıza gönderildi.')
    else:
        messages.info(request, 'Yeni kod istemeden önce kısa bir süre bekleyin.')
    return redirect('accounts:verify_email_2fa')

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
        
    orders = request.user.orders.select_related(
        'shipment',
        'shipment__company',
        'shipment__current_station',
    ).prefetch_related('shipment__events').order_by('-created_at')
    
    return render(request, 'accounts/profile.html', {
        'form': form,
        'orders': orders
    })
