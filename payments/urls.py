from django.urls import path
from . import views

urlpatterns = [
    path('',                views.payment_list,   name='payment_list'),
    path('<int:pk>/',       views.payment_detail, name='payment_detail'),
    path('<int:pk>/pay/',   views.mark_paid,      name='mark_paid'),
    path("process/<int:pk>/", views.process_payment, name="process_payment"),
]