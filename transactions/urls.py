from django.urls import path

from . import views

urlpatterns = [
    path("history/", views.transaction_history, name="transaction_history"),
    path("airtime/buy/", views.buy_airtime, name="buy_airtime"),
    path("electricity/buy/", views.pay_electricity, name="pay_electricity"),
    path("data/buy/", views.buy_data, name="buy_data"),
    path(
        "electricity/receipt/<str:reference>/",
        views.electricity_receipt,
        name="electricity_receipt",
    ),
    path("airtime/receipt/<str:reference>/", views.airtime_receipt, name="airtime_receipt"),
    path("data/receipt/<str:reference>/", views.data_receipt, name="data_receipt"),
    path("webhook/vtpass/", views.vtpass_webhook, name="vtpass_webhook"),
]
