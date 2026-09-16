import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.text import slugify
from django.utils import timezone
from django.db.models import F
from .models import Package
from stakeholder.models import AgentKYC
from django.utils.dateparse import parse_date
from .models import Package, PackageType
from decimal import Decimal
from datetime import datetime
from utils.emails import (
    send_package_created_emails,
    send_package_updated_emails,
    send_package_deleted_emails,
)
@login_required
def create_packages(request):
    agent_kyc = AgentKYC.objects.filter(user=request.user).first()
    package_types = PackageType.objects.all()

    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            package_type_id = request.POST.get('package_type')
            price_raw = request.POST.get('price')
            total_seats_raw = request.POST.get('total_seats')
            duration_days_raw = request.POST.get('duration_days')
            departure_date_raw = request.POST.get('departure_date')
            application_deadline_raw = request.POST.get('application_deadline')

            if not all([name, package_type_id, price_raw, total_seats_raw, duration_days_raw, departure_date_raw]):
                messages.error(request, "Please fill in all required (*) fields.")
                return render(request, 'stakeholder/create_package.html', {
                    'agent_kyc': agent_kyc,
                    'package_types': package_types
                })

            price = Decimal(price_raw)
            total_seats = int(total_seats_raw)
            duration_days = int(duration_days_raw)

            departure_date = datetime.strptime(departure_date_raw, '%Y-%m-%d').date()
            application_deadline = (
                datetime.strptime(application_deadline_raw, '%Y-%m-%d').date()
                if application_deadline_raw else None
            )

            package_type = PackageType.objects.get(id=package_type_id)

            country = request.POST.get('country', 'Saudi Arabia')
            city = request.POST.get('city', 'Makkah')
            tier = request.POST.get('tier', 'standard')
            makkah_hotel = request.POST.get('makkah_hotel', '')
            madinah_hotel = request.POST.get('madinah_hotel', '')
            description = request.POST.get('description', '')

            visa = request.POST.get('visa') == 'on'
            ticket = request.POST.get('ticket') == 'on'
            transport = request.POST.get('transport') == 'on'
            ziyarat = request.POST.get('ziyarat') == 'on'
            meals = request.POST.get('meals') == 'on'

            banner_image = request.FILES.get('banner')

            Package.objects.create(
                agency=request.user,
                name=name,
                package_type=package_type,
                country=country,
                city=city,
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
                meals=meals,
                description=description,
                banner=banner_image
            )

            messages.success(request, "Package published successfully!")
            return redirect('packages:manage_packages')

        except PackageType.DoesNotExist:
            messages.error(request, "Selected Package Type is invalid.")
        except ValueError:
            messages.error(request, "Please enter valid numeric values and dates (YYYY-MM-DD).")
        except Exception as e:
            messages.error(request, f"Server Error: {str(e)}")

    context = {
        'agent_kyc': agent_kyc,
        'package_types': package_types,
    }
    return render(request, 'stakeholder/add_packages.html', context)
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