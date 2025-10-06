from django.shortcuts import render

def test_template(request):
    return render(request, 'test.html')

def home(request):
   return render(request, "frontoffice/pages/home.html")