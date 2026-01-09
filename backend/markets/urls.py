from django.urls import path

from . import views

urlpatterns = [
    path('markets/', views.market_list, name='market-list'),
    path('markets/<slug:slug>/', views.market_detail, name='market-detail'),
    path('markets/<slug:slug>/trade/', views.trade_market, name='market-trade'),
]
