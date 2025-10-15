from django.shortcuts import render, redirect
from django.contrib import messages
from .models import User
import re
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.conf import settings
from .utils import email_verification_token
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST


def test_template(request):
    return render(request, 'test.html')


def home(request):
    return render(request, "frontoffice/pages/home.html")


@login_required
def delete_account_view(request):
    if request.method == 'POST':
        confirm = request.POST.get('confirm', '')  # Champ venant du formulaire
        if confirm == 'DELETE':
            user = request.user
            # Soft delete: on peut juste désactiver le compte et flagger comme supprimé
            user.is_active = False
            user.username = f'deleted_user_{user.pk}'  # Pour éviter conflit usernames
            user.email = f'deleted_{user.pk}@example.com'  # Pour éviter conflit emails
            user.save()
            
            # Déconnexion de l'utilisateur après suppression
            logout(request)
            messages.success(request, "Your account has been permanently deleted.")
            return redirect('home')
        else:
            messages.error(request, "You must type 'DELETE' to confirm account deletion.")
            return redirect('profile')

    return render(request, 'frontoffice/pages/delete_account.html')

def signin_view(request):
    context = {
        'errors': {},
        'values': {}
    }

    if request.user.is_authenticated:
        return redirect_based_on_role(request.user)

    if request.method == 'POST':
        username_or_email = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        context['values']['username'] = username_or_email
        has_errors = False

        if not username_or_email:
            context['errors']['username'] = 'Username or email is required.'
            has_errors = True
        if not password:
            context['errors']['password'] = 'Password is required.'
            has_errors = True

        if not has_errors:
            user = authenticate(request, username=username_or_email, password=password)
            if user is None:
                try:
                    user_obj = User.objects.get(email=username_or_email)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    user = None

            if user is not None:
                if not user.is_email_verified:
                    context['errors']['general'] = 'Please verify your email before logging in.'
                else:
                    login(request, user)
                    next_url = request.GET.get('next', 'journalist_dashboard' if user.role == User.JOURNALIST else 'dashboard')
                    return redirect(next_url)
            else:
                context['errors']['general'] = 'Invalid username/email or password. Please try again.'

    return render(request, 'frontoffice/pages/login.html', context)


def signup_view(request):
    context = {
        'errors': {},
        'values': {}
    }

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirmPassword', '')

        context['values']['username'] = username
        context['values']['email'] = email

        has_errors = False

        # Username validation
        if not username:
            context['errors']['username'] = 'Username is required.'
            has_errors = True
        elif User.objects.filter(username=username).exists():
            context['errors']['username'] = 'This username is already taken.'
            has_errors = True
        elif len(username) < 3:
            context['errors']['username'] = 'Username must be at least 3 characters long.'
            has_errors = True

        # Email validation
        if not email:
            context['errors']['email'] = 'Email is required.'
            has_errors = True
        elif User.objects.filter(email=email).exists():
            context['errors']['email'] = 'A user with this email already exists.'
            has_errors = True
        elif '@' not in email or '.' not in email:
            context['errors']['email'] = 'Please enter a valid email address.'
            has_errors = True

        # Password validation
        if not password:
            context['errors']['password'] = 'Password is required.'
            has_errors = True
        else:
            pattern = r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[\W_]).{8,}$'
            if not re.match(pattern, password):
                context['errors']['password'] = 'Password must be at least 8 characters and include uppercase, lowercase, number, and special character.'
                has_errors = True

        if not confirm_password:
            context['errors']['confirmPassword'] = 'Please confirm your password.'
            has_errors = True
        elif password != confirm_password:
            context['errors']['confirmPassword'] = 'Passwords do not match.'
            has_errors = True

        if not has_errors:
            # Créer l'utilisateur désactivé
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role=User.JOURNALIST,
                is_active=False  # Désactiver le compte tant que l'email n'est pas vérifié
            )

            # Générer token et uid
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = email_verification_token.make_token(user)

            # Construire le lien de vérification
            verification_link = request.build_absolute_uri(
                f"/users/verify-email/{uid}/{token}/"
            )

            # Envoyer l'email
            subject = "Verify your MindLens account"
            message = render_to_string("frontoffice/emails/verify_email.html", {
                "user": user,
                "verification_link": verification_link
            })
            email_message = EmailMessage(subject, message, to=[user.email])
            email_message.content_subtype = "html"
            email_message.send()

            messages.success(request, "Account created! Please check your email to verify your account.")
            return redirect('signin')
        else:
            # Reset sensitive fields
            if 'password' in context['errors'] or 'confirmPassword' in context['errors']:
                context['values']['password'] = ''
                context['values']['confirmPassword'] = ''
            if 'username' in context['errors']:
                context['values']['username'] = ''
            if 'email' in context['errors']:
                context['values']['email'] = ''

    return render(request, 'frontoffice/pages/register.html', context)


def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and email_verification_token.check_token(user, token):
        user.is_email_verified = True
        user.is_active = True  # Activer le compte
        user.save()
        messages.success(request, "Email verified successfully! You can now log in.")
        return redirect('signin')
    else:
        return HttpResponse("Verification link is invalid or expired.")


@login_required
def logout_view(request):
    logout(request)
    return redirect('signin')


@login_required
def journalist_dashboard_view(request):
    return render(request, 'frontoffice/pages/dashboard.html')


@login_required
def admin_dashboard_view(request):
    return render(request, 'backoffice/pages/dashboard.html')


def redirect_based_on_role(user):
    if user.role == User.ADMIN:
        return redirect('dashboard')
    elif user.role == User.JOURNALIST:
        return redirect('journalist_dashboard')
    else:
        return redirect('signin')


def handle_profile_update(request, context):
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    username = request.POST.get('username', '').strip()

    try:
        if first_name:
            request.user.first_name = first_name
        if last_name:
            request.user.last_name = last_name

        if username and username != request.user.username:
            if len(username) < 3:
                context['errors']['username'] = 'Username must be at least 3 characters long.'
            elif User.objects.filter(username=username).exclude(pk=request.user.pk).exists():
                context['errors']['username'] = 'This username is already taken.'
            else:
                request.user.username = username

        if not context['errors']:
            request.user.save()
            messages.success(request, 'Profile updated successfully!')
            context['success'] = True
            return True
        return False

    except Exception:
        context['errors']['general'] = 'An error occurred while updating your profile. Please try again.'
        return False


def handle_profile_image_update(request, context):
    if 'profile_image' in request.FILES:
        profile_image = request.FILES['profile_image']

        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if profile_image.content_type not in allowed_types:
            context['errors']['profile_image'] = 'Please upload a valid image file (JPEG, PNG, GIF, WebP).'
            return False
        elif profile_image.size > 5 * 1024 * 1024:
            context['errors']['profile_image'] = 'Image file too large. Maximum size is 5MB.'
            return False
        else:
            if request.user.profile_image:
                request.user.profile_image.delete(save=False)
            request.user.profile_image = profile_image
            request.user.save()
            messages.success(request, 'Profile image updated successfully!')
            return True
    return False


def handle_password_update(request, context):
    current_password = request.POST.get('current_password', '').strip()
    new_password = request.POST.get('new_password', '').strip()
    confirm_password = request.POST.get('confirm_password', '').strip()

    has_errors = False

    if not current_password:
        context['password_errors']['current_password'] = 'Current password is required.'
        has_errors = True
    elif not request.user.check_password(current_password):
        context['password_errors']['current_password'] = 'Current password is incorrect.'
        has_errors = True

    if not new_password:
        context['password_errors']['new_password'] = 'New password is required.'
        has_errors = True
    else:
        try:
            validate_password(new_password, request.user)
        except ValidationError as e:
            context['password_errors']['new_password'] = ' '.join(e.messages)
            has_errors = True

    if not confirm_password:
        context['password_errors']['confirm_password'] = 'Please confirm your new password.'
        has_errors = True
    elif new_password != confirm_password:
        context['password_errors']['confirm_password'] = 'New passwords do not match.'
        has_errors = True

    if not has_errors:
        try:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password updated successfully!')
            context['password_success'] = True
            return True
        except Exception:
            context['password_errors']['general'] = 'An error occurred while updating your password. Please try again.'
            return False

    return False


@login_required
def profile_view(request):
    context = {
        'user': request.user,
        'errors': {},
        'success': False,
        'password_errors': {},
        'password_success': False
    }

    if request.method == 'POST':
        section = request.POST.get('section', 'profile')

        if section == 'password':
            password_updated = handle_password_update(request, context)
            if password_updated:
                return redirect('profile')

        elif section == 'profile':
            image_updated = handle_profile_image_update(request, context)
            if image_updated:
                return redirect('profile')

            profile_updated = handle_profile_update(request, context)
            if profile_updated:
                return redirect('profile')

    return render(request, 'frontoffice/pages/profile.html', context)
