from django.shortcuts import render, redirect, get_object_or_404
from .models import Notification

def get_user_notifications(request):
    if not request.user.is_authenticated:
        return {
            'notifications': [],
            'unread_count': 0
        }

   
    notifications = request.user.notifications.filter(is_deleted=False)[:10] 
    unread_count = request.user.notifications.filter(is_read=False, is_deleted=False).count()
    
    return {
        'notifications': notifications,
        'unread_count': unread_count
    }


def mark_as_read(request, slug):
    
    if not request.user.is_authenticated:
        return redirect('accounts:login') 
    notification = get_object_or_404(Notification, slug=slug, recipient=request.user)
    notification.is_read = True
    notification.save()
    
    
    if notification.redirect_url:
        return redirect(notification.redirect_url)
    return redirect(request.META.get('HTTP_REFERER', '/'))