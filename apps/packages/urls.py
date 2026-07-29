from django.urls import path
from . import views

app_name = "packages"

urlpatterns = [

    path(
        'create-package/',
        views.create_packages,
        name='create_packages'
    ),
path('package/detail/<int:package_id>/', views.packages_detail, name='packages_detail'),
    path(
        'manage-packages/',
        views.manage_packages,
        name='manage_packages'
    ),

    path(
        'update-package/<int:pk>/',
        views.update_package,
        name='update_package'
    ),

    path(
        'delete-package/<int:pk>/',
        views.delete_package,
        name='delete_package'
    ),
]