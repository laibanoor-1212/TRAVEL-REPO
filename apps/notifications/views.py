import re
from django.shortcuts import redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse, NoReverseMatch, resolve
from django.contrib.auth.decorators import login_required
from .models import Notification

@login_required
def get_user_notifications(request):
    unread_qs = Notification.objects.filter(
        recipient=request.user, 
        is_read=False
    ).order_by('-created_at')
    
    data = []
    for n in unread_qs:
        data.append({
            'slug': n.slug,
            'title': n.title,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime("%b %d, %H:%M") if n.created_at else ''
        })

    return JsonResponse({
        'count': unread_qs.count(),
        'notifications': data
    })


@login_required
def mark_as_read(request, slug):
    notification = get_object_or_404(Notification, slug=slug, recipient=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])


    target = str(notification.redirect_url or '').strip()
    if not target or target in ['', '#', 'None', 'null']:
        if hasattr(notification, 'payment') and notification.payment:
            target = f"/payments/{notification.payment.id}/"
        elif hasattr(notification, 'booking') and notification.booking:
            target = f"/bookings/{notification.booking.id}/"
        elif hasattr(notification, 'ticket') and notification.ticket:
            target = f"/tickets/{notification.ticket.id}/"

    digits = re.findall(r'\d+', target) if target else []
    entity_id = int(digits[0]) if digits else None
    if 'booking' in target or 'payment' in target or 'status' in target:
        if entity_id:
          
            if getattr(request.user, 'role', '') == 'customer':
                if 'choose-payment' in target:
                    res = _safe_redirect('bookings:choose_payment_method', booking_id=entity_id)
                    if res: return res
                elif 'stripe' in target:
                    res = _safe_redirect('bookings:stripe_checkout', booking_id=entity_id)
                    if res: return res
                elif 'raast' in target:
                    res = _safe_redirect('bookings:raast_payment', booking_id=entity_id)
                    if res: return res
                elif 'status' in target or 'payment' in target:
                    res = _safe_redirect('bookings:payment_status', booking_id=entity_id)
                    if res: return res
                res = _safe_redirect('customers:user_bookings')
                if res: return res
            elif getattr(request.user, 'role', '') in ['agent', 'travel_agent', 'stakeholder']:
                if 'payment' in target:
                    res = _safe_redirect('agent:payment_detail', payment_id=entity_id)
                    if res: return res
                res = _safe_redirect('agent:booking_detail', booking_id=entity_id)
                if res: return res

           
            elif request.user.is_staff or request.user.is_superuser:
                if 'payment' in target:
                    res = _safe_redirect('adminpanel:admin_payment_detail', payment_id=entity_id)
                    if res: return res
                res = _safe_redirect('adminpanel:admin_booking_detail', booking_id=entity_id)
                if res: return res
    if 'ticket' in target or 'complaint' in target or 'support' in target:
        if entity_id:
            if request.user.is_staff or request.user.is_superuser:
                res = _safe_redirect('adminpanel:ticket_detail', ticket_id=entity_id)
                if res: return res
            elif getattr(request.user, 'role', '') in ['agent', 'travel_agent', 'stakeholder']:
                res = _safe_redirect('agent:ticket_detail', ticket_id=entity_id)
                if res: return res
            else:
                res = _safe_redirect('customers:ticket_detail', ticket_id=entity_id)
                if res: return res
    
        if request.user.is_staff or request.user.is_superuser:
            res = _safe_redirect('adminpanel:admin_complaints')
            if res: return res
        elif getattr(request.user, 'role', '') in ['agent', 'travel_agent', 'stakeholder']:
            res = _safe_redirect('agent:agent_tickets')
            if res: return res
        res = _safe_redirect('customers:user_tickets')
        if res: return res
    if 'package' in target:
        if 'create' in target:
            res = _safe_redirect('packages:create_packages')
            if res: return res
        elif 'manage' in target:
            res = _safe_redirect('packages:manage_packages')
            if res: return res
        elif entity_id:
            if 'update' in target:
                res = _safe_redirect('packages:update_package', pk=entity_id)
                if res: return res
            res = _safe_redirect('packages:packages_detail', package_id=entity_id)
            if res: return res
    try:
        return redirect(reverse(target))
    except NoReverseMatch:
        pass

    if target.startswith('/'):
        try:
            resolve(target)
            return redirect(target)
        except Exception:
            pass
    return _safe_role_fallback(request)


def _safe_redirect(view_name, *args, **kwargs):
    try:
        return redirect(reverse(view_name, args=args, kwargs=kwargs))
    except NoReverseMatch:
        return None


def _safe_role_fallback(request):
    referer = request.META.get('HTTP_REFERER')
    if referer and referer != request.build_absolute_uri():
        return redirect(referer)

    user = request.user
    if user.is_staff or user.is_superuser:
        return _safe_redirect('adminpanel:admin_dashboard') or redirect('/')
    elif getattr(user, 'role', '') in ['agent', 'travel_agent', 'stakeholder']:
        return _safe_redirect('agent:dashboard') or redirect('/')
    else:
        return _safe_redirect('customers:user_bookings') or redirect('/')