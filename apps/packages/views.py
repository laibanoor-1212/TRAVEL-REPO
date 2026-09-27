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
from decimal import Decimal, InvalidOperation
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
            # 1. Required text & date inputs
            name = request.POST.get('name', '').strip()
            package_type_id = request.POST.get('package_type')
            departure_city = request.POST.get('departure_city', 'Lahore').strip()
            price_raw = request.POST.get('price')
            total_seats_raw = request.POST.get('total_seats')
            duration_days_raw = request.POST.get('duration_days')
            departure_date_raw = request.POST.get('departure_date')
            application_deadline_raw = request.POST.get('application_deadline')
            if not all([name, package_type_id, departure_city, price_raw, total_seats_raw, duration_days_raw, departure_date_raw]):
                messages.error(request, "Please fill in all required (*) fields.")
                return render(request, 'stakeholder/add_packages.html', {
                    'agent_kyc': agent_kyc,
                    'package_types': package_types
                })

            # 2. Numeric & Date parsing
            price = Decimal(price_raw)
            total_seats = int(total_seats_raw)
            duration_days = int(duration_days_raw)
            departure_date = datetime.strptime(departure_date_raw, '%Y-%m-%d').date()
            application_deadline = (
                datetime.strptime(application_deadline_raw, '%Y-%m-%d').date()
                if application_deadline_raw else None
            )

            package_type = PackageType.objects.get(id=package_type_id)
            type_name = (package_type.name or '').lower()
            country = request.POST.get('country', '').strip() or ('Saudi Arabia' if 'umrah' in type_name or 'hajj' in type_name else '')
            city = request.POST.get('city', '').strip() or ('Makkah' if 'umrah' in type_name or 'hajj' in type_name else '')
            tier = request.POST.get('tier', 'standard')
            sharing_type = request.POST.get('sharing_type', 'quad')

            makkah_hotel = request.POST.get('makkah_hotel', '').strip()
            madinah_hotel = request.POST.get('madinah_hotel', '').strip()

            makkah_dist_raw = request.POST.get('makkah_distance_meters') or request.POST.get('hotel_distance_meters')
            madinah_dist_raw = request.POST.get('madinah_distance_meters')

            makkah_distance_meters = int(makkah_dist_raw) if makkah_dist_raw and makkah_dist_raw.isdigit() else None
            madinah_distance_meters = int(madinah_dist_raw) if madinah_dist_raw and madinah_dist_raw.isdigit() else None
            visa = request.POST.get('visa') == 'on'
            ticket = request.POST.get('ticket') == 'on'
            transport = request.POST.get('transport') == 'on'
            ziyarat = request.POST.get('ziyarat') == 'on'
            meals = request.POST.get('meals') == 'on'
            airline_name = request.POST.get('airline_name', '').strip()
            flight_type = request.POST.get('flight_type', 'direct')
            is_direct_flight = (flight_type == 'direct') or (request.POST.get('is_direct_flight') == 'on')
            description = request.POST.get('description', '').strip()
            banner_image = request.FILES.get('banner')

            Package.objects.create(
                agency=request.user,
                name=name,
                package_type=package_type,
                tier=tier,
                country=country,
                city=city,
                departure_city=departure_city,
                price=price,
                sharing_type=sharing_type,
                total_seats=total_seats,
                duration_days=duration_days,
                departure_date=departure_date,
                application_deadline=application_deadline,
                makkah_hotel=makkah_hotel,
                makkah_distance_meters=makkah_distance_meters,
                madinah_hotel=madinah_hotel,
                madinah_distance_meters=madinah_distance_meters,
                visa=visa,
                ticket=ticket,
                transport=transport,
                ziyarat=ziyarat,
                meals=meals,
                airline_name=airline_name,
                is_direct_flight=is_direct_flight,
                description=description,
                banner=banner_image if banner_image else 'package_banners/default.jpg',
                status='active'
            )

            messages.success(request, "Package published successfully!")
            return redirect('packages:manage_packages')

        except PackageType.DoesNotExist:
            messages.error(request, "Selected Package Type is invalid.")
        except (ValueError, InvalidOperation):
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
        try:
            # Basic Specifications
            package.name = request.POST.get('name', package.name).strip()
            
            type_id = request.POST.get('package_type')
            if type_id:
                package.package_type = PackageType.objects.get(id=type_id)

            package.tier = request.POST.get('tier', package.tier)
            package.country = request.POST.get('country', package.country).strip()
            package.city = request.POST.get('city', package.city).strip()
            
            # Numeric & Capacity Fields
            price_raw = request.POST.get('price')
            if price_raw:
                package.price = Decimal(price_raw)

            advance_raw = request.POST.get('advance_amount')
            if advance_raw:
                package.advance_amount = Decimal(advance_raw)
            elif advance_raw == '':
                package.advance_amount = Decimal('0.00')

            total_seats_raw = request.POST.get('total_seats')
            if total_seats_raw:
                package.total_seats = int(total_seats_raw)

            duration_raw = request.POST.get('duration_days')
            if duration_raw:
                package.duration_days = int(duration_raw)

            # Dates Parsing
            dep_date_raw = request.POST.get('departure_date')
            if dep_date_raw:
                package.departure_date = datetime.strptime(dep_date_raw, '%Y-%m-%d').date()

            app_deadline_raw = request.POST.get('application_deadline')
            if app_deadline_raw:
                package.application_deadline = datetime.strptime(app_deadline_raw, '%Y-%m-%d').date()
            elif app_deadline_raw == '':
                package.application_deadline = None

            # Accommodation & Flights
            package.makkah_hotel = request.POST.get('makkah_hotel', package.makkah_hotel).strip()
            package.madinah_hotel = request.POST.get('madinah_hotel', package.madinah_hotel).strip()
            package.airline_name = request.POST.get('airline_name', package.airline_name).strip()
            package.flight_type = request.POST.get('flight_type', package.flight_type)
            package.description = request.POST.get('description', package.description).strip()

            # Included Services (Checkboxes)
            package.visa = 'visa' in request.POST
            package.ticket = 'ticket' in request.POST
            package.transport = 'transport' in request.POST
            package.ziyarat = 'ziyarat' in request.POST
            package.meals = 'meals' in request.POST
            package.guide = 'guide' in request.POST

            # File Uploads
            if request.FILES.get('banner'):
                package.banner = request.FILES['banner']

            package.save()

            # Send Email Notification
            try:
                send_package_updated_emails(request.user, package)
            except Exception:
                pass  

            messages.success(request, "Package updated successfully.")
            return redirect('stakeholder:manage_packages')

        except PackageType.DoesNotExist:
            messages.error(request, "Selected Package Type is invalid.")
        except (ValueError, InvalidOperation):
            messages.error(request, "Please check form values for valid format.")
        except Exception as e:
            messages.error(request, f"Error updating package: {str(e)}")

    context = {
        'package': package,
        'package_types': package_types,
    }
    return render(request, 'stakeholder/edit_packages.html', context)


@login_required
def delete_package(request, pk):
    package = get_object_or_404(Package, pk=pk, agency=request.user)
    
    package.is_active = False
    package.status = 'inactive'
    package.save()

    try:
        send_package_deleted_emails(request.user, package)
    except Exception:
        pass

    messages.success(request, "Package moved to inactive tab successfully.")
    return redirect('packages:manage_packages')
@login_required
def manage_packages(request):
    today = timezone.now().date()
    

    Package.objects.filter(
        agency=request.user,
        application_deadline__lt=today,
        status='active'
    ).update(status='inactive')

    active_packages = Package.objects.filter(
        agency=request.user, 
        status='active',
        package_type__is_active=True,
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