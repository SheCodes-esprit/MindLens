from django.shortcuts import render, redirect
from django.contrib import messages
from .models import User
import re
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.http import HttpResponse
from .utils import email_verification_token
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.db.models import Q
password_reset_token = PasswordResetTokenGenerator()
from .utils import email_verification_token, generate_otp, is_otp_valid 
from django.utils import timezone
from django.contrib.sessions.models import Session
from .models import UserSession

from datetime import datetime, time


from django.contrib.admin.views.decorators import staff_member_required

from django.db.models import Count, Avg
from datetime import timedelta
from users.models import User

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def test_template(request):
    return render(request, 'test.html')

def home(request):
    return render(request, "frontoffice/pages/home.html")

from django.shortcuts import render


def signin_view(request):
    context = {'errors': {}, 'values': {}}

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
                elif user.is_2fa_enabled:
                    otp = generate_otp()
                    user.otp_code = otp
                    user.otp_created_at = timezone.now()
                    user.save()
                    
                    subject = "Your MindLens Login Code"
                    message = render_to_string("frontoffice/emails/otp_email.html", {
                        "user": user,
                        "otp": otp
                    })
                    email_message = EmailMessage(subject, message, to=[user.email])
                    email_message.content_subtype = "html"
                    email_message.send()
                    
                    # Store user ID in session for 2FA verification
                    request.session['2fa_user_id'] = user.pk
                    messages.success(request, "A verification code has been sent to your email.")
                    return redirect('verify_2fa_login')
                else:
                    # No 2FA, login directly
                    login(request, user)
                    next_url = request.GET.get('next', 'home' if user.role == User.JOURNALIST else 'dashboard')
                    return redirect(next_url)
            else:
                context['errors']['general'] = 'Invalid username/email or password. Please try again.'

    return render(request, 'frontoffice/pages/login.html', context)

def signup_view(request):
    context = {'errors': {}, 'values': {}}

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
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role=User.JOURNALIST,
                is_active=False
            )
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = email_verification_token.make_token(user)
            verification_link = request.build_absolute_uri(f"/users/verify-email/{uid}/{token}/")

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

    return render(request, 'frontoffice/pages/register.html', context)


def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and email_verification_token.check_token(user, token):
        user.is_email_verified = True
        user.is_active = True
        user.save()
        messages.success(request, "Email verified successfully! You can now log in.")
        return redirect('signin')
    else:
        return HttpResponse("Verification link is invalid or expired.")


@login_required
def logout_view(request):
    logout(request)
    return redirect('signin')


# --------------------- Mot de passe oublié / reset ---------------------
def forgot_password_view(request):
    if request.method == "POST":
        email = request.POST.get('email', '').strip()
        if not email:
            messages.error(request, "Please enter your email address.")
        else:
            try:
                user = User.objects.get(email=email)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = password_reset_token.make_token(user)
                reset_link = request.build_absolute_uri(
                    f"/users/reset-password/{uid}/{token}/"
                )
                subject = "Reset your MindLens password"
                message = render_to_string("frontoffice/emails/reset_password_email.html", {
                    "user": user,
                    "reset_link": reset_link
                })
                email_message = EmailMessage(subject, message, to=[user.email])
                email_message.content_subtype = "html"
                email_message.send()
                messages.success(request, "Password reset email sent! Check your inbox.")
                return redirect('signin')
            except User.DoesNotExist:
                messages.error(request, "No user found with this email address.")

    return render(request, "frontoffice/pages/forgot_password.html")


def reset_password_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not password_reset_token.check_token(user, token):
        messages.error(request, "Password reset link is invalid or expired.")
        return redirect('forgot_password')

    if request.method == "POST":
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        errors = {}

        if not new_password:
            errors['new_password'] = "New password is required."
        else:
            try:
                validate_password(new_password, user)
            except ValidationError as e:
                errors['new_password'] = ' '.join(e.messages)

        if new_password != confirm_password:
            errors['confirm_password'] = "Passwords do not match."

        if not errors:
            user.set_password(new_password)
            user.save()
            messages.success(request, "Password updated successfully! You can now log in.")
            return redirect('signin')
        else:
            return render(request, "frontoffice/pages/reset_password.html", {"errors": errors})

    return render(request, "frontoffice/pages/reset_password.html", {"errors": {}})


# --------------------- Dashboard ---------------------
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


# --------------------- Profile ---------------------
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


# --------------------- Supprimer compte ---------------------
@login_required
def delete_account_view(request):
    if request.method == 'POST':
        confirm = request.POST.get('confirm', '')
        if confirm == 'DELETE':
            user = request.user
            user.is_active = False
            user.username = f'deleted_user_{user.pk}'
            user.email = f'deleted_{user.pk}@example.com'
            user.save()
            logout(request)
            messages.success(request, "Your account has been permanently deleted.")
            return redirect('home')
        else:
            messages.error(request, "You must type 'DELETE' to confirm account deletion.")
            return redirect('profile')

    return render(request, 'frontoffice/pages/delete_account.html')


@login_required
def list_users_view(request):
    if not request.user.is_admin():
        messages.error(request, "You do not have permission to access this page.")
        return redirect('journalist_dashboard' if request.user.is_journalist() else 'signin')

    # Start with all users
    users = User.objects.all()
    
    # Get filter parameters from GET request
    search_query = request.GET.get('search', '').strip()
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    verified_filter = request.GET.get('verified', '')
    
    # Apply search filter - searches across username, email, first_name, last_name
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    # Apply role filter (JOURNALIST or ADMIN)
    if role_filter:
        users = users.filter(role=role_filter)
    
    # Apply status filter (active/inactive)
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    # Apply email verification filter (verified/not_verified)
    if verified_filter == 'verified':
        users = users.filter(is_email_verified=True)
    elif verified_filter == 'not_verified':
        users = users.filter(is_email_verified=False)
    
    # Order by username and get count
    users = users.order_by('username')
    users_count = users.count()

    # Pass everything to template
    context = {
        'users': users,
        'users_count': users_count,  # This is the stat - filtered user count
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'verified_filter': verified_filter,
    }
    return render(request, 'backoffice/pages/list_users.html', context)
@login_required
def add_user_view(request):
    if not request.user.is_admin():
        messages.error(request, "You do not have permission to access this page.")
        return redirect('journalist_dashboard' if request.user.is_journalist() else 'signin')

    context = {'errors': {}, 'values': {}}

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirmPassword', '')
        role = request.POST.get('role', '')
        profile_image = request.FILES.get('profile_image')

        context['values']['first_name'] = first_name
        context['values']['last_name'] = last_name
        context['values']['username'] = username
        context['values']['email'] = email
        context['values']['role'] = role

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

        # Role validation
        if role not in [User.JOURNALIST, User.ADMIN]:
            context['errors']['role'] = 'Invalid role selected.'
            has_errors = True

        # Profile image validation
        if profile_image:
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if profile_image.content_type not in allowed_types:
                context['errors']['profile_image'] = 'Please upload a valid image file (JPEG, PNG, GIF, WebP).'
                has_errors = True
            elif profile_image.size > 5 * 1024 * 1024:
                context['errors']['profile_image'] = 'Image file too large. Maximum size is 5MB.'
                has_errors = True

        if not has_errors:
            try:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    role=role,
                    is_active=False,
                    is_email_verified=False
                )
                if profile_image:
                    user.profile_image = profile_image
                    user.save()

                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = email_verification_token.make_token(user)
                verification_link = request.build_absolute_uri(f"/users/verify-email/{uid}/{token}/")

                subject = "Verify your MindLens account"
                message = render_to_string("frontoffice/emails/verify_email.html", {
                    "user": user,
                    "verification_link": verification_link
                })
                email_message = EmailMessage(subject, message, to=[user.email])
                email_message.content_subtype = "html"
                email_message.send()

                messages.success(request, "User created successfully! An email verification link has been sent to the user.")
                return redirect('list_users')
            except Exception as e:
                context['errors']['general'] = f'An error occurred: {str(e)}'
                has_errors = True

    return render(request, 'backoffice/pages/add_user.html', context)

@login_required
def delete_user_view(request, user_id):
    if not request.user.is_admin():
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('journalist_dashboard' if request.user.is_journalist() else 'signin')
    
    try:
        user = User.objects.get(pk=user_id)
        if user == request.user:
            messages.error(request, "You cannot delete your own account from this page.")
            return redirect('list_users')
        
        username = user.username  # Store username for success message
        user.delete()  # Hard delete the user
        messages.success(request, f"User {username} has been deleted successfully.")
    except User.DoesNotExist:
        messages.error(request, "The user you are trying to delete does not exist.")
    
    return redirect('list_users')
@login_required
def edit_user_view(request, user_id):
    if not request.user.is_admin():
        messages.error(request, "You do not have permission to access this page.")
        return redirect('journalist_dashboard' if request.user.is_journalist() else 'signin')

    try:
        user_to_edit = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        messages.error(request, "The user you are trying to edit does not exist.")
        return redirect('list_users')

    context = {'errors': {}, 'values': {}, 'user_to_edit': user_to_edit}

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        role = request.POST.get('role', '')
        is_active = request.POST.get('is_active') == 'on'
        is_email_verified = request.POST.get('is_email_verified') == 'on'
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        profile_image = request.FILES.get('profile_image')

        context['values']['username'] = username
        context['values']['email'] = email
        context['values']['first_name'] = first_name
        context['values']['last_name'] = last_name
        context['values']['role'] = role

        has_errors = False

        # Username validation
        if not username:
            context['errors']['username'] = 'Username is required.'
            has_errors = True
        elif username != user_to_edit.username and User.objects.filter(username=username).exists():
            context['errors']['username'] = 'This username is already taken.'
            has_errors = True
        elif len(username) < 3:
            context['errors']['username'] = 'Username must be at least 3 characters long.'
            has_errors = True

        # Email validation
        if not email:
            context['errors']['email'] = 'Email is required.'
            has_errors = True
        elif email != user_to_edit.email and User.objects.filter(email=email).exists():
            context['errors']['email'] = 'A user with this email already exists.'
            has_errors = True
        elif '@' not in email or '.' not in email:
            context['errors']['email'] = 'Please enter a valid email address.'
            has_errors = True

        # Role validation
        if role not in [User.JOURNALIST, User.ADMIN]:
            context['errors']['role'] = 'Invalid role selected.'
            has_errors = True

        # Password validation (only if provided)
        if new_password:
            pattern = r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[\W_]).{8,}$'
            if not re.match(pattern, new_password):
                context['errors']['new_password'] = 'Password must be at least 8 characters and include uppercase, lowercase, number, and special character.'
                has_errors = True
            elif new_password != confirm_password:
                context['errors']['confirm_password'] = 'Passwords do not match.'
                has_errors = True

        # Profile image validation
        if profile_image:
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if profile_image.content_type not in allowed_types:
                context['errors']['profile_image'] = 'Please upload a valid image file (JPEG, PNG, GIF, WebP).'
                has_errors = True
            elif profile_image.size > 5 * 1024 * 1024:
                context['errors']['profile_image'] = 'Image file too large. Maximum size is 5MB.'
                has_errors = True

        if not has_errors:
            try:
                user_to_edit.username = username
                user_to_edit.email = email
                user_to_edit.first_name = first_name
                user_to_edit.last_name = last_name
                user_to_edit.role = role
                user_to_edit.is_active = is_active
                user_to_edit.is_email_verified = is_email_verified

                if new_password:
                    user_to_edit.set_password(new_password)

                if profile_image:
                    if user_to_edit.profile_image:
                        user_to_edit.profile_image.delete(save=False)
                    user_to_edit.profile_image = profile_image

                user_to_edit.save()

                messages.success(request, f"User {username} has been updated successfully.")
                return redirect('list_users')
            except Exception as e:
                context['errors']['general'] = f'An error occurred: {str(e)}'
                has_errors = True

    return render(request, 'backoffice/pages/edit_user.html', context)

#--------------------- 2FA ---------------------
@login_required
def enable_2fa_view(request):
    print("Enable 2FA view called")  # <-- debug
    if request.method == "POST":
        if request.user.is_2fa_enabled:
            messages.warning(request, "2FA is already enabled on your account.")
            return redirect('profile')

        otp = generate_otp()
        request.user.otp_code = otp
        request.user.otp_created_at = timezone.now()
        request.user.save()

        print(f"OTP generated: {otp}")  # <-- debug

        # send email
        subject = "Enable Two-Factor Authentication - MindLens"
        message = render_to_string("frontoffice/emails/otp_email.html", {
            "user": request.user,
            "otp": otp
        })
        email_message = EmailMessage(subject, message, to=[request.user.email])
        email_message.content_subtype = "html"
        email_message.send()
        print(f"OTP email sent to {request.user.email}")  # <-- debug

        messages.success(request, "OTP sent to your email. Please verify to enable 2FA.")
        return redirect('verify_2fa_setup')
    else:
        return redirect('profile')

@login_required
def verify_2fa_setup(request):
    """Verify OTP to enable 2FA"""
    context = {'errors': {}}
    
    if request.user.is_2fa_enabled:
        messages.warning(request, "2FA is already enabled.")
        return redirect('profile')
    
    if request.method == 'POST':
        otp_input = request.POST.get('otp', '').strip()
        
        if not otp_input:
            context['errors']['otp'] = 'OTP is required.'
        elif not is_otp_valid(request.user.otp_created_at):
            context['errors']['otp'] = 'OTP has expired. Please request a new one.'
        elif otp_input != request.user.otp_code:
            context['errors']['otp'] = 'Invalid OTP. Please try again.'
        else:
            # Enable 2FA
            request.user.is_2fa_enabled = True
            request.user.otp_code = None
            request.user.otp_created_at = None
            request.user.save()
            messages.success(request, "Two-Factor Authentication enabled successfully!")
            return redirect('profile')
    
    return render(request, 'frontoffice/pages/verify_2fa.html', context)

@login_required
def disable_2fa_view(request):
    """Disable 2FA"""
    if request.method == 'POST':
        request.user.is_2fa_enabled = False
        request.user.otp_code = None
        request.user.otp_created_at = None
        request.user.save()
        messages.success(request, "Two-Factor Authentication disabled.")
        return redirect('profile')
    
    return render(request, 'frontoffice/pages/disable_2fa.html')

def verify_2fa_login(request):
    """Verify OTP during login"""
    context = {'errors': {}}
    
    # Get user_id from session (set during password verification)
    user_id = request.session.get('2fa_user_id')
    
    if not user_id:
        messages.error(request, "Session expired. Please log in again.")
        return redirect('signin')
    
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('signin')
    
    if request.method == 'POST':
        otp_input = request.POST.get('otp', '').strip()
        
        if not otp_input:
            context['errors']['otp'] = 'OTP is required.'
        elif not is_otp_valid(user.otp_created_at):
            context['errors']['otp'] = 'OTP has expired. Please log in again.'
            del request.session['2fa_user_id']
            return redirect('signin')
        elif otp_input != user.otp_code:
            context['errors']['otp'] = 'Invalid OTP. Please try again.'
        else:
            # OTP verified, log in user
            login(request, user)
            user.otp_code = None
            user.otp_created_at = None
            user.save()
            del request.session['2fa_user_id']
            messages.success(request, "Logged in successfully!")
            return redirect_based_on_role(user)
    
    context['user_email'] = user.email
    return render(request, 'frontoffice/pages/verify_2fa_login.html', context)

#--------------------- Active Sessions ---------------------

@login_required
def active_sessions_view(request):
    # Get all active sessions for the user
    user_sessions = UserSession.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('user')
    
    # Clean up expired sessions
    for user_session in user_sessions:
        try:
            Session.objects.get(session_key=user_session.session_key)
        except Session.DoesNotExist:
            user_session.is_active = False
            user_session.save()
    
    # Refresh active sessions
    active_sessions = user_sessions.filter(is_active=True)
    
    # Mark current session
    current_session_key = request.session.session_key
    
    context = {
        'sessions': active_sessions,
        'current_session_key': current_session_key,
        'total_sessions': active_sessions.count(),
        'suspicious_sessions': active_sessions.filter(is_suspicious=True).count(),
    }
    
    return render(request, 'frontoffice/pages/active_sessions.html', context)


@login_required
def terminate_session_view(request, session_id):
    if request.method == 'POST':
        try:
            user_session = UserSession.objects.get(
                id=session_id,
                user=request.user
            )
            
            # Prevent terminating current session
            if user_session.session_key == request.session.session_key:
                messages.error(request, "You cannot terminate your current session.")
                return redirect('active_sessions')
            
            # Delete Django session
            try:
                session = Session.objects.get(session_key=user_session.session_key)
                session.delete()
            except Session.DoesNotExist:
                pass
            
            # Mark user session as inactive
            user_session.is_active = False
            user_session.save()
            
            messages.success(request, f"Session from {user_session.device_type} ({user_session.location}) has been terminated.")
        except UserSession.DoesNotExist:
            messages.error(request, "Session not found.")
    
    return redirect('active_sessions')


@login_required
def terminate_all_sessions_view(request):
    if request.method == 'POST':
        current_session_key = request.session.session_key
        
        # Get all user sessions except current
        user_sessions = UserSession.objects.filter(
            user=request.user,
            is_active=True
        ).exclude(session_key=current_session_key)
        
        count = 0
        for user_session in user_sessions:
            try:
                session = Session.objects.get(session_key=user_session.session_key)
                session.delete()
                count += 1
            except Session.DoesNotExist:
                pass
            
            user_session.is_active = False
            user_session.save()
        
        messages.success(request, f"Successfully terminated {count} session(s).")
        return redirect('active_sessions')
    
    return redirect('active_sessions')