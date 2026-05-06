from django.urls import path
from . import views

urlpatterns = [
    path("", views.maintenance_list, name="maintenance_list"),
    path("create/", views.create_request, name="maintenance_create"),
    path("<int:pk>/", views.maintenance_detail, name="maintenance_detail"),
    path("<int:pk>/update/", views.update_status, name="maintenance_update"),
]