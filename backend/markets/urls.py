from django.urls import path

from . import views
from .api import auth

urlpatterns = [
    path('markets/', views.market_list, name='market-list'),
    path('markets/<slug:slug>/', views.market_detail, name='market-detail'),
    path('markets/<slug:slug>/trade/', views.trade_market, name='market-trade'),
    path('markets/<slug:slug>/resolve/', views.resolve_market, name='resolve_market'),
    path('markets/<slug:slug>/redeem/', views.redeem_shares, name='redeem_shares'),
    path('markets/<slug:slug>/delete/', views.delete_market, name='delete_market'),
    path('markets/<slug:slug>/ledger/', views.market_ledger, name='market_ledger'),
    path('markets/<slug:slug>/comments/', views.market_comments, name='market_comments'),
    path('portfolio/', views.user_portfolio, name='user_portfolio'),
    
    # Auth Endpoints
    path('auth/login/', auth.login_view, name='login'),
    path('auth/logout/', auth.logout_view, name='auth-logout'),
    path('auth/signup/', auth.signup_view, name='auth-signup'),
    path('auth/me/', auth.me_view, name='auth-me'),
]
