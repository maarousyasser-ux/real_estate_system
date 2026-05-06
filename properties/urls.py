# properties/urls.py
from django.urls import path
from . import views

# properties/urls.py
urlpatterns = [
    path('', views.property_list, name='property_list'),     
    path('add/', views.property_create, name='property_create'),
    
    path('<int:pk>/', views.property_detail, name='property_detail'),
    path('<int:pk>/edit/', views.property_edit, name='property_edit'),
    path('<int:pk>/status/', views.change_status, name='change_status'),
    path('<int:pk>/', views.property_detail, name='property_detail'),
    path('confirm/<int:pk>/', views.confirm_property, name='confirm_property'),
    path('submit-request/', views.submit_maintenance_request, name='submit_request'),
]