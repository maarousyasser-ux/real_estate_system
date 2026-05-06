from django.urls import path
from . import views

urlpatterns = [
    path('', views.tenant_list, name='tenant_list'),
    path('assign/<int:property_id>/', views.assign_tenant, name='assign_tenant'),
]