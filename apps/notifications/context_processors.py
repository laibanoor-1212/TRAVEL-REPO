from .models import Notification

def notification_context(request):
    if request.user.is_authenticated:
        # Fetch unread notifications for the logged-in user
        user_notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
        unread_count = user_notifications.filter(is_read=False).count()
        
        return {
            'notifications': user_notifications[:10],  # Top 5 notifications for dropdown
            'unread_count': unread_count,
        }
    
    return {
        'notifications': [],
        'unread_count': 0,
    }