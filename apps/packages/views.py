import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.text import slugify
from django.utils import timezone
from django.db.models import F
from .models import Package
from django.utils.dateparse import parse_date
from .models import Package, PackageType
from utils.emails import (
    send_package_created_emails,
    send_package_updated_emails,
    send_package_deleted_emails,
)

@login_required
def create_packages(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        package_type_id = request.POST.get('package_type')
        tier = request.POST.get('tier', 'standard')
        country = request.POST.get('country', 'Saudi Arabia').strip()
        city = request.POST.get('city', 'Makkah').strip()
        
        price = request.POST.get('price')
        total_seats = request.POST.get('total_seats', 50)
        duration_days = request.POST.get('duration_days', 15)
        
        departure_date_str = request.POST.get('departure_date')
        application_deadline_str = request.POST.get('application_deadline')
        
        makkah_hotel = request.POST.get('makkah_hotel', '').strip() or None
        madinah_hotel = request.POST.get('madinah_hotel', '').strip() or None
        description = request.POST.get('description', '').strip()
        visa = request.POST.get('visa') == 'on'
        ticket = request.POST.get('ticket') == 'on'
        transport = request.POST.get('transport') == 'on'
        ziyarat = request.POST.get('ziyarat') == 'on'
        meals = request.POST.get('meals') == 'on'

        banner_file = request.FILES.get('banner')
        if not name or not package_type_id or not price or not departure_date_str:
            messages.error(request, "Tamam zaroori (Required) fields fill karein.")
            return render(request, 'stakeholder/create_package.html', {
                'package_types': PackageType.objects.filter(is_active=True)
            })

        try:
            price_val = float(price)
            if price_val < 100000 or price_val > 2500000:
                messages.error(request, "Price  is between PKR 100,000  and PKR 2,500,000.")
                return render(request, 'stakeholder/create_package.html', {
                    'package_types': PackageType.objects.filter(is_active=True)
                })
        except ValueError:
            messages.error(request, "Sahi price enter karein.")
            return render(request, 'stakeholder/create_package.html', {
                'package_types': PackageType.objects.filter(is_active=True)
            })

        package_type = get_object_or_404(PackageType, id=package_type_id)
        departure_date = parse_date(departure_date_str)
        application_deadline = parse_date(application_deadline_str) if application_deadline_str else departure_date

        if application_deadline and departure_date and application_deadline > departure_date:
            messages.error(request, "Application deadline is not after departure date")
            return render(request, 'stakeholder/create_package.html', {
                'package_types': PackageType.objects.filter(is_active=True)
            })

        try:
            package = Package(
                agency=request.user, 
                name=name,
                package_type=package_type,
                tier=tier,
                country=country,
                city=city,
                price=price_val,
                total_seats=int(total_seats) if total_seats else 50,
                duration_days=int(duration_days) if duration_days else 15,
                departure_date=departure_date,
                application_deadline=application_deadline,
                makkah_hotel=makkah_hotel,
                madinah_hotel=madinah_hotel,
                visa=visa,
                ticket=ticket,
                transport=transport,
                ziyarat=ziyarat,
                meals=meals,
                description=description if description else 'Package details coming soon...',
                status='active',
            )
            if banner_file:
                package.banner = banner_file
            package.save()

            messages.success(request, f"Package '{package.name}' is created sucessfully!")
            return redirect('packages:manage_packages')

        except Exception as e:
            messages.error(request, f"error in saving package: {str(e)}")
    package_types = PackageType.objects.filter(is_active=True)
    return render(request, 'stakeholder/add_packages.html', {
        'package_types': package_types
    })

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
    today = timezone.now().date()
    active_packages = Package.objects.filter(
        agency=request.user, 
        status='active',
        application_deadline__gte=today,
        booked_seats__lt=F('total_seats')
    ).order_by('-created_at')
    inactive_packages = Package.objects.filter(
        agency=request.user
    ).exclude(
        id__in=active_packages.values_list('id', flat=True)
    ).order_by('-created_at')

    context = {
        'active_packages': active_packages,
        'inactive_packages': inactive_packages,
        'today': today,
    }
    
    return render(request, 'stakeholder/manage_packages.html', context)
def packages_detail(request, package_id):
    package = get_object_or_404(Package, id=package_id)
    return render(request, 'stakeholder/packages_detail.html', {'package': package})