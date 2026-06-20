from django.shortcuts import render
from packages.models import Package 

def hajj_packages(request):
    active_packages = Package.objects.filter(status='active').order_by('-created_at')
    
    return render(request, 'base/hajjpackages.html', {'packages': active_packages})