from django.urls import path

from . import views
from . import claimlab_views
from .api import auth

urlpatterns = [
    path('health/', views.health_check, name='health-check'),
    path('markets/', views.market_list, name='market-list'),
    path('markets/<slug:slug>/', views.market_detail, name='market-detail'),
    path('markets/<slug:slug>/trade/', views.trade_market, name='market-trade'),
    path('markets/<slug:slug>/resolve/', views.resolve_market, name='resolve_market'),
    path('markets/<slug:slug>/redeem/', views.redeem_shares, name='redeem_shares'),
    path('markets/<slug:slug>/delete/', views.delete_market, name='delete_market'),
    path('markets/<slug:slug>/ledger/', views.market_ledger, name='market_ledger'),
    path('markets/<slug:slug>/comments/', views.market_comments, name='market_comments'),
    path('portfolio/', views.user_portfolio, name='user_portfolio'),

    # Invitation-only Claim Lab
    path('claim-lab/config/', claimlab_views.claim_lab_config, name='claim_lab_config'),
    path('claim-lab/sources/', claimlab_views.source_list, name='claim_lab_sources'),
    path('claim-lab/sources/<int:source_id>/', claimlab_views.source_detail, name='claim_lab_source'),
    path('claim-lab/sources/<int:source_id>/retry/', claimlab_views.source_retry, name='claim_lab_retry'),
    path('claim-lab/sources/<int:source_id>/transcript/', claimlab_views.source_transcript, name='claim_lab_transcript'),
    path('claim-lab/sources/<int:source_id>/claims/', claimlab_views.source_claims, name='claim_lab_source_claims'),
    path('claim-lab/claims/<int:claim_id>/', claimlab_views.claim_detail, name='claim_lab_claim'),
    path('claim-lab/claims/<int:claim_id>/publish/', claimlab_views.claim_publish, name='claim_lab_publish'),
    
    # Auth Endpoints
    path('auth/login/', auth.login_view, name='login'),
    path('auth/logout/', auth.logout_view, name='auth-logout'),
    path('auth/signup/', auth.signup_view, name='auth-signup'),
    path('auth/me/', auth.me_view, name='auth-me'),
]
