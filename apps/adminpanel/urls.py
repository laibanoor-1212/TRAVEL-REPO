from django.urls import path
from django.contrib.auth import views as auth_views
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
    path('complaints/', views.admin_complaints, name='admin_complaints'),
    path('payments/', views.admin_payments_list, name='admin_payments_list'),
    path('payments/<int:payment_id>/', views.admin_payment_detail, name='payment_detail'),
    
    # Action Route to Release Payout
    path('payments/<int:payment_id>/release/', views.admin_release_payout, name='admin_release_payout'),
    path('payments/proof/<int:proof_id>/verify/', views.admin_verify_proof, name='verify_proof'),
    path('payments/proof/<int:proof_id>/reject/', views.admin_reject_proof, name='reject_proof'),
    path('payments/<int:payment_id>/release/', views.admin_release_payment, name='release_payment'),
    path('payments/<int:payment_id>/cancel/', views.admin_cancel_payment, name='cancel_payment'),
   path('payments/<int:payment_id>/refund/', views.admin_refund_payment, name='admin_refund_payment'),
    path('package-types/add/', views.add_package_type, name='add_package_type'),
    path('package-types/delete/<int:pk>/', views.delete_package_type, name='delete_package_type'),
    path('admin-dashboard/commission-setting/', views.set_commission, name='set_commission'),
    path('settings/', views.admin_settings_view, name='admin_settings'),
    path('settings/change-password/', 
         auth_views.PasswordChangeView.as_view(
         template_name='adminpanel/admin_change_password.html',
         success_url='/adminpanel/settings/'), name='admin_change_password'),

    path('settings/download-backup/', views.download_db_backup, name='download_db_backup'),
    path("guides/", views.guide_list, name="guide_list"),
    path("guides/edit/<slug:page_slug>/",views.admin_guide_edit,name="admin_guide_edit",),
    path("guides/delete/<slug:page_slug>/",views.delete_guide,name="admin_guide_delete",),
    path("api/save-guide/<slug:page_slug>/",views.api_save_guide,name="api_save_guide",),
]