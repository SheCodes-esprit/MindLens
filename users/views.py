from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from .models import User
import re

def test_template(request):
    return render(request, 'test.html')

def home(request):
   return render(request, "frontoffice/pages/home.html")

def signin_view(request):
    return render(request, 'frontoffice/pages/login.html')


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

def logout_view(request):
    return render(request, 'frontoffice/pages/home.html')