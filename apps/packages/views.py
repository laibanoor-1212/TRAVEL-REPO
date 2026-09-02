import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.text import slugify

from .models import Package, PackageType
from utils.emails import (
    send_package_created_emails,
    send_package_updated_emails,
    send_package_deleted_emails,
)

@login_required
def create_packages(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        package_type_id = request.POST.get('package_type')
        price = request.POST.get('price')
        tier = request.POST.get('tier', 'standard')
        total_seats = request.POST.get('total_seats', 50)
        duration_days = request.POST.get('duration_days', 15)
        departure_date = request.POST.get('departure_date')
        application_deadline = request.POST.get('application_deadline') or departure_date
        makkah_hotel = request.POST.get('makkah_hotel')
        madinah_hotel = request.POST.get('madinah_hotel')
        description = request.POST.get('description')
        banner = request.FILES.get('banner')

        # Checkbox values
        visa = 'visa' in request.POST
        ticket = 'ticket' in request.POST
        transport = 'transport' in request.POST
        ziyarat = 'ziyarat' in request.POST

        package_type = get_object_or_404(PackageType, id=package_type_id)

        # FIX: Yahan 'email' argument HATA DIYA gaya hai
        package = Package.objects.create(
            agency=request.user,  # Agency automatically user se attach ho rahi hai
            name=name,
            package_type=package_type,
            price=price,
            tier=tier,
            total_seats=total_seats,
            duration_days=duration_days,
            departure_date=departure_date,
            application_deadline=application_deadline,
            makkah_hotel=makkah_hotel,
            madinah_hotel=madinah_hotel,
            visa=visa,
            ticket=ticket,
            transport=transport,
            ziyarat=ziyarat,
            description=description,
            banner=banner if banner else 'package_banners/default.jpg'
        )

        messages.success(request, "Package successfully created!")
        return redirect('packages:manage_packages')

    package_types = PackageType.objects.filter(is_active=True)
    return render(request, 'stakeholder/add_packages.html', {'package_types': package_types})


@login_required
def update_package(request, pk):
    package = get_object_or_404(Package, pk=pk, agency=request.user)
    package_types = PackageType.objects.filter(is_active=True) if hasattr(PackageType, 'is_active') else PackageType.objects.all()

    if request.method == 'POST':
        package.name = request.POST.get('name')
        
        type_id = request.POST.get('package_type')
        if type_id:
            package.package_type_id = type_id

        package.tier = request.POST.get('tier', package.tier)
        package.country = request.POST.get('country', package.country)
        package.city = request.POST.get('city', package.city)
        package.price = request.POST.get('price', package.price)
        package.total_seats = request.POST.get('total_seats', package.total_seats)
        package.duration_days = request.POST.get('duration_days', package.duration_days)
        package.departure_date = request.POST.get('departure_date', package.departure_date)
        package.application_deadline = request.POST.get('application_deadline', package.application_deadline)
        package.makkah_hotel = request.POST.get('makkah_hotel', package.makkah_hotel)
        package.madinah_hotel = request.POST.get('madinah_hotel', package.madinah_hotel)
        package.description = request.POST.get('description', package.description)

        package.visa = 'visa' in request.POST
        package.ticket = 'ticket' in request.POST
        package.transport = 'transport' in request.POST
        package.ziyarat = 'ziyarat' in request.POST

        if request.FILES.get('banner'):
            package.banner = request.FILES['banner']

        package.save()

        # Email Notification
        send_package_updated_emails(request.user, package)

        messages.success(request, "Package updated successfully.")
        return redirect('packages:manage_packages')

    context = {
        'package': package,
        'package_types': package_types,
    }
    return render(request, 'stakeholder/edit_packages.html', context)


@login_required
def delete_package(request, pk):
    package = get_object_or_404(Package, pk=pk, agency=request.user)
    
    # Both fields update karein taake filter query sahi chale
    package.is_active = False
    package.status = 'inactive'
    package.save()

    # Deactivation Email Notification
    send_package_deleted_emails(request.user, package)

    messages.success(request, "Package moved to inactive tab successfully.")
    return redirect('stakeholder:manage_packages')


@login_required
def manage_packages(request):
    # 'is_active=True' ki jagah 'status='active'' use kiya hai
    active_packages = Package.objects.filter(
        agency=request.user, 
        status='active'
    ).order_by('-created_at')
    
    # Inactive / Draft / Closed packages
    other_packages = Package.objects.filter(
        agency=request.user
    ).exclude(
        status='active'
    ).order_by('-created_at')

    context = {
        'active_packages': active_packages,
        'other_packages': other_packages,
    }
    
    return render(request, 'stakeholder/manage_packages.html', context)

def packages_detail(request, package_id):
    package = get_object_or_404(Package, id=package_id)
    return render(request, 'stakeholder/packages_detail.html', {'package': package})