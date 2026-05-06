from django.urls import path
from . import views

app_name = "rentals"

urlpatterns = [
    # This is the missing link that was causing the NoReverseMatch
    path("request/<int:property_id>/", views.request_rent, name="request_rent"),
    
    path("requests/", views.rental_requests, name="rental_requests"),
    path("approve/<int:pk>/", views.approve_request, name="approve_request"),
    path("reject/<int:pk>/", views.reject_request, name="reject_request"),
]