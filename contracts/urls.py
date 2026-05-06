from django.urls import path
from . import views

urlpatterns = [
    path('',                        views.contract_list,      name='contract_list'),
    path('create/',                 views.contract_create,    name='contract_create'),
    path('<int:pk>/',               views.contract_detail,    name='contract_detail'),
    path('<int:pk>/terminate/',     views.contract_terminate, name='contract_terminate'),
    path('contract_list/', views.contract_list, name='contract_list'),
     path("approve/<int:pk>/", views.contract_approve, name="contract_approve"),
    path("decline/<int:pk>/", views.contract_decline, name="contract_decline"),
]