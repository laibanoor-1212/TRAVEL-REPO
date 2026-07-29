from django.shortcuts import render

def home(request):
    return render(request, 'base/home.html')

def packages(request):
    return render(request, 'base/hajjpackages.html')

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
