from django.shortcuts import render,redirect

# Create your views here.
def create_profile(request):
    return render(request, 'stakeholder/create_profile.html')