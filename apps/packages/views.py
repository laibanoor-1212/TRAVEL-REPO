from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import PackageForm
from .models import Package,PackageType
from django.shortcuts import redirect, get_object_or_404

def create_packages(request):

    if request.method == "POST":
        form = PackageForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Package created successfully."
            )

            return redirect('stakeholder:manage_packages')

    else:
        form = PackageForm()

    return render(
        request,
        'stakeholder/create_packages.html',
        {'form': form}
    )
def update_package(request, pk):
    package = get_object_or_404(Package, pk=pk)
    
  
    package_types = PackageType.objects.all() 

    if request.method == 'POST':
        package.name = request.POST.get('name')
    
        type_id = request.POST.get('package_type')
        if type_id:
            package.package_type_id = type_id
            
        package.tier = request.POST.get('tier')
        package.country = request.POST.get('country')
        package.city = request.POST.get('city')
        package.price = request.POST.get('price')
        package.total_seats = request.POST.get('total_seats')
        package.duration_days = request.POST.get('duration_days')
        package.departure_date = request.POST.get('departure_date')
        package.application_deadline = request.POST.get('application_deadline')
        package.makkah_hotel = request.POST.get('makkah_hotel')
        package.madinah_hotel = request.POST.get('madinah_hotel')
        package.visa = 'visa' in request.POST
        package.ticket = 'ticket' in request.POST
        package.transport = 'transport' in request.POST
        package.ziyarat = 'ziyarat' in request.POST
        if request.FILES.get('banner'):
            package.banner = request.FILES['banner']

        package.save()
       
        return redirect('stakeholder:manage-packages') 

   
    context = {
        'package': package,
        'package_types': package_types, 
    }
    
   
    return render(request, 'stakeholder/edit_packages.html', context)
def delete_package(request, pk):
   
    package = get_object_or_404(
        Package, 
        pk=pk, 
        agency=request.user
    )
    package.status = 'inactive'
    package.save()

    messages.success(
        request,
        "Package moved to inactive tab successfully."
    )

    return redirect('stakeholder:manage_packages')



def manage_packages(request):
    active_packages = Package.objects.filter(
        agency=request.user,
        status='active'
    ).order_by('-created_at')
    inactive_packages = Package.objects.filter(
        agency=request.user
    ).exclude(
        status='active'
    ).order_by('-created_at')

    return render(
        request,
        'stakeholder/manage_packages.html',
        {
            'active_packages': active_packages,
            'inactive_packages': inactive_packages,
        }
    )
def packages_detail(request, package_id):
       
   
    package = get_object_or_404(Package, id=package_id)
    
    context = {
        'package': package,
    }
    return render(request, 'stakeholder/packages_detail.html', context)
