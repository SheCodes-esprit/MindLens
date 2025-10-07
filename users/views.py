from django.shortcuts import render, redirect
from django.contrib import messages
from .models import User
import re
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

def test_template(request):
    return render(request, 'test.html')

def home(request):
   return render(request, "frontoffice/pages/home.html")


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
        
        if not username:
            context['errors']['username'] = 'Username is required.'
            has_errors = True
        elif User.objects.filter(username=username).exists():
            context['errors']['username'] = 'This username is already taken.'
            has_errors = True
        elif len(username) < 3:
            context['errors']['username'] = 'Username must be at least 3 characters long.'
            has_errors = True
        else:
            pass
        
        if not email:
            context['errors']['email'] = 'Email is required.'
            has_errors = True
        elif User.objects.filter(email=email).exists():
            context['errors']['email'] = 'A user with this email already exists.'
            has_errors = True
        elif '@' not in email or '.' not in email:
            context['errors']['email'] = 'Please enter a valid email address.'
            has_errors = True
        else:
            pass
        
        if not password:
            context['errors']['password'] = 'Password is required.'
            has_errors = True
        else:
            pattern = r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[\W_]).{8,}$'
            if not re.match(pattern, password):
                context['errors']['password'] = 'Password must be at least 8 characters and include uppercase, lowercase, number, and special character.'
                has_errors = True
            else:
                pass
        
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
                    role=User.JOURNALIST
                )
                
                return redirect('signin') 
        else:
            if 'password' in context['errors'] or 'confirmPassword' in context['errors']:
                context['values']['password'] = ''
                context['values']['confirmPassword'] = ''
            
            if 'username' in context['errors']:
                context['values']['username'] = ''
            
            if 'email' in context['errors']:
                context['values']['email'] = ''
    
    return render(request, 'frontoffice/pages/register.html', context)

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

@login_required
def profile_view(request):
    context = {
        'user': request.user,
        'errors': {},
        'success': False
    }
    
    if request.method == 'POST':
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
                elif request.user.__class__.objects.filter(username=username).exclude(pk=request.user.pk).exists():
                    context['errors']['username'] = 'This username is already taken.'
                else:
                    request.user.username = username
            
            if not context['errors']:
                request.user.save()
                messages.success(request, 'Profile updated successfully!')
                context['success'] = True
                
        except Exception as e:
            context['errors']['general'] = 'An error occurred while updating your profile. Please try again.'
    
    return render(request, 'frontoffice/pages/profile.html', context)

@login_required
def change_password_view(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        errors = {}
        
        if not request.user.check_password(current_password):
            errors['current_password'] = 'Current password is incorrect.'
        
        if new_password:
            pattern = r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[\W_]).{8,}$'
            if not re.match(pattern, new_password):
                errors['new_password'] = 'Password must be at least 8 characters and include uppercase, lowercase, number, and special character.'
        
        if new_password != confirm_password:
            errors['confirm_password'] = 'New passwords do not match.'
        
        if not errors:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)  
            messages.success(request, 'Password changed successfully!')
            return redirect('profile')
        else:
            for field, error in errors.items():
                messages.error(request, error)
    
    return redirect('profile')