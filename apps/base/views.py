from django.shortcuts import render
from packages.models import Package
from packages.models import PackageType 

def home(request):
    # Admin dwara add kiye gaye tamam package types fetch kar rahe hain
    package_types = PackageType.objects.all().order_by('-id')
    
    context = {
        'package_types': package_types,
    }
    return render(request, 'base/home.html', context)

def packages(request):
    return render(request, 'base/hajjpackages.html')
def about(request):
    return render(request, 'base/about.html')

def hajjpackages(request):
    return render(request, 'base/hajjpackages.html')

def Guide(request):
    return render(request, 'base/Guide.html')

def hajj_guide(request):
    return render(request, 'base/Guide.html')

def ziyarat(request):
    return render(request, 'base/about.html')
def hajj_packages(request):
    active_packages = Package.objects.filter(status='active').order_by('-created_at')
    
    return render(request, 'packages/hajjpackages.html', {'packages': active_packages})
