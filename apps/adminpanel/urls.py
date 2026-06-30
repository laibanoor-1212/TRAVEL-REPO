from django.urls import path
from . import views

app_name='adminpanel'

urlpatterns = [
    path('login/', views.admin_login_view, name='admin_login'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('logout/', views.admin_logout_view, name='admin_logout'),
    path('forget_password/', views.admin_forget_password, name='admin_forget_password'),
    path("reset_confirm/<uidb64>/<token>/",views.admin_reset_password_confirm, name="reset_confirm"),
    path('agent_requests',views.agent_requests,name='agent_requests'),
  path('review/<int:pk>/', views.review_agent, name='review_agent'),
  path('packages/monitoring/', views.admin_packages, name='admin_packages'),
    path('packages/<int:pkg_id>/block/', views.block_package, name='block_package'),
    path('packages/<int:pkg_id>/unblock/', views.unblock_package, name='unblock_package'),
    path('packages/<int:pkg_id>/remove/', views.remove_package, name='remove_package'),
    path('customers/', views.admin_customer, name='admin_customer'),
    path('customers/<int:profile_id>/', views.customer_detail, name='customer_detail'),
    path('bookings/', views.admin_bookings, name='admin_bookings'),
    path('bookings/update/<int:booking_id>/', views.update_booking_status, name='update_booking_status'),
]