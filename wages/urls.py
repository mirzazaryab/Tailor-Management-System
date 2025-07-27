# wages/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Core Dashboard & Daily Operations
    path('', views.dashboard, name='dashboard'),
    path('add-tailor/', views.add_tailor, name='add_tailor'),

    # Product Management
    path('add-product/', views.add_product, name='add_product'),


    # Daily Work / Reports (Non-Order Specific)
    path('record-work/', views.record_work, name='record_work'),
    path('daily-report/', views.daily_report, name='daily_report'),

]