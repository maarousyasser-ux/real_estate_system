from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('users.urls')),
    path('properties/', include('properties.urls')),
    path('tenants/', include('tenants.urls')),
    path('payments/', include('payments.urls')),


    path('community/', include(('community.urls', 'community'), namespace='community')),

    path('contracts/', include('contracts.urls')),


    path('messages/', include(('real_estate_messages.urls', 'real_estate_messages'), namespace='real_estate_messages')),
    
    path("maintenance/", include("maintenance.urls")),
     path('notifications/', include('notifications.urls')),
path("rentals/", include(("rentals.urls", "rentals"), namespace="rentals")),
]