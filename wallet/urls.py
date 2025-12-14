

from django.urls import path
from . import views

urlpatterns = [
    path('info/', views.wallet_info, name='wallet_info'),
    path('fund/', views.fund_wallet, name='fund_wallet'),
    path('verify/<str:reference>/', views.verify_payment, name='verify_payment'),
    path('webhook/', views.paystack_webhook, name='paystack_webhook'),
    # path('withdraw/', views.demo_withdraw, name='demo_withdraw'),  # Remove in production
]
