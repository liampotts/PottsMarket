import json
from decimal import Decimal

from django.db import connection
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from .models import Market, Outcome, Position, Comment
from .services import CPMMService


def serialize_market(market):
    source_claim = getattr(market, 'source_claim', None)
    source_payload = None
    if source_claim:
        source = source_claim.document.source
        source_payload = {
            'title': source.title,
            'author': source.author,
            'url': source.url,
            'excerpt': source_claim.excerpt,
            'excerpt_start_seconds': source_claim.excerpt_start_seconds,
            'resolution_criteria': source_claim.resolution_criteria,
            'resolution_source_url': source_claim.resolution_source_url,
            'closes_at': source_claim.closes_at.isoformat(),
            'resolves_at': source_claim.resolves_at.isoformat(),
            'extraction_method': source_claim.extraction_method,
        }

    latest_agent_forecast = None
    forecasts = list(market.forecasts.all()) if hasattr(market, 'forecasts') else []
    if forecasts:
        forecast = forecasts[0]
        latest_agent_forecast = {
            'agent_name': forecast.agent_name,
            'probability': float(forecast.probability),
            'rationale': forecast.rationale,
            'created_at': forecast.created_at.isoformat(),
        }

    return {
        'id': market.id,
        'title': market.title,
        'slug': market.slug,
        'description': market.description,
        'status': market.status,
        'created_at': market.created_at.isoformat(),
        'created_by': market.created_by.username if market.created_by else None,
        'outcomes': [
            {
                'id': outcome.id,
                'name': outcome.name,
                'price': outcome.current_price,
                'pool': outcome.pool_balance,
            }
            for outcome in market.outcomes.all()
        ],
        'source': source_payload,
        'agent_forecast': latest_agent_forecast,
    }


def health_check(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:
        return JsonResponse({'status': 'unhealthy'}, status=503)

    return JsonResponse({'status': 'ok'})


@csrf_exempt
def market_list(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required.'}, status=401)

        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON body.'}, status=400)

        title = (payload.get('title') or '').strip()
        slug = (payload.get('slug') or '').strip()
        description = (payload.get('description') or '').strip()
        status = (payload.get('status') or Market.STATUS_DRAFT).strip()

        errors = {}
        if not title:
            errors['title'] = 'Title is required.'
        if not slug:
            errors['slug'] = 'Slug is required.'
        elif Market.objects.filter(slug=slug).exists():
            errors['slug'] = 'Slug already exists.'

        if status not in dict(Market.STATUS_CHOICES):
            errors['status'] = 'Invalid status.'

        if errors:
            return JsonResponse({'errors': errors}, status=400)

        market = Market.objects.create(
            title=title,
            slug=slug,
            description=description,
            status=status,
            created_by=request.user
        )

        # Auto-initialize 50/50 outcomes
        CPMMService.initialize_market(market)

        response_payload = serialize_market(market)
        return JsonResponse(response_payload, status=201)

    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    markets = Market.objects.select_related(
        'created_by',
        'source_claim__document__source',
    ).prefetch_related('outcomes', 'forecasts')
    payload = [serialize_market(market) for market in markets]
    return JsonResponse(payload, safe=False)


@csrf_exempt
def market_detail(request, slug):
    market = get_object_or_404(
        Market.objects.select_related(
            'created_by',
            'source_claim__document__source',
        ).prefetch_related('outcomes', 'forecasts'),
        slug=slug,
    )

    if request.method in ['PUT', 'PATCH']:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required.'}, status=401)
        
        # Allow staff/superusers to edit any market
        is_admin = request.user.is_staff or request.user.is_superuser
        if market.created_by != request.user and not is_admin:
            return JsonResponse({'error': 'Permission denied.'}, status=403)

        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON body.'}, status=400)

        market.title = payload.get('title', market.title)
        market.description = payload.get('description', market.description)
        market.status = payload.get('status', market.status)
        
        # If slug is updated, we need to handle it carefully or disallow it.
        # For simplicity, we'll allow it but check uniqueness if changed.
        new_slug = payload.get('slug')
        if new_slug and new_slug != market.slug:
             if Market.objects.filter(slug=new_slug).exists():
                 return JsonResponse({'error': 'Slug already exists.'}, status=400)
             market.slug = new_slug

        market.save()
        # Fall through to return updated object

    if request.method not in ['GET', 'PUT', 'PATCH']:
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    payload = serialize_market(market)
    return JsonResponse(payload)


@csrf_exempt
def trade_market(request, slug):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    market = get_object_or_404(Market, slug=slug)

    if market.status != Market.STATUS_OPEN:
        return JsonResponse({'error': 'This market is not open for trading.'}, status=400)
    
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON body.'}, status=400)

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=401)
    
    user = request.user

    outcome_id = payload.get('outcome_id')
    amount = payload.get('amount')

    if not outcome_id or not amount:
        return JsonResponse({'error': 'outcome_id and amount are required.'}, status=400)

    try:
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid amount.'}, status=400)

    try:
        outcome = market.outcomes.get(pk=outcome_id)
    except Outcome.DoesNotExist:
         return JsonResponse({'error': 'Outcome not found.'}, status=404)

    # Initialize market if needed (ensure pools exist)
    if outcome.pool_balance == 0:
        CPMMService.initialize_market(market)
        outcome.refresh_from_db()

    try:
        result = CPMMService.buy_tokens(user, outcome, amount)
    except ValueError as error:
        return JsonResponse({'error': str(error)}, status=400)

    return JsonResponse({
        'status': 'success',
        'trade': result,
        'market_status': {
            'outcomes': [
                {
                    'id': o.id,
                    'name': o.name,
                    'price': o.current_price,
                    'pool': o.pool_balance
                } for o in market.outcomes.all()
            ]
        }
    })


@csrf_exempt
def resolve_market(request, slug):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    market = get_object_or_404(Market, slug=slug)

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=401)

    is_admin = request.user.is_staff or request.user.is_superuser
    if market.created_by != request.user and not is_admin:
        return JsonResponse({'error': 'Permission denied.'}, status=403)

    if market.status == Market.STATUS_RESOLVED:
        return JsonResponse({'error': 'Market is already resolved.'}, status=400)
    
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
        outcome_id = payload.get('outcome_id')
        outcome = market.outcomes.get(pk=outcome_id)
    except (ValueError, TypeError, Outcome.DoesNotExist):
        return JsonResponse({'error': 'Invalid outcome_id.'}, status=400)

    market.winning_outcome = outcome
    market.status = Market.STATUS_RESOLVED
    market.save()
    
    return JsonResponse({'status': 'resolved', 'winner': outcome.name})


@csrf_exempt
def redeem_shares(request, slug):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    market = get_object_or_404(Market, slug=slug)
    if market.status != Market.STATUS_RESOLVED or not market.winning_outcome:
        return JsonResponse({'error': 'Market is not resolved.'}, status=400)

    payload = json.loads(request.body.decode('utf-8') or '{}')
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=401)
    
    user = request.user

    # Find position in winning outcome
    try:
        position = Position.objects.get(user=user, outcome=market.winning_outcome)
        shares = position.shares
        if shares <= 0:
             return JsonResponse({'message': 'No shares to redeem.', 'payout': 0})
             
        # "Redeem" means giving them $1 per share. 
        # In a real app, we would add to user balance.
        # Here we just zero out the shares and return the payout amount.
        payout = float(shares) * 1.00
        
        position.shares = Decimal('0')
        position.save()
        
        # Credit Balance
        user.userprofile.balance += Decimal(str(payout))
        user.userprofile.save()
        
        return JsonResponse({'status': 'redeemed', 'payout': payout, 'shares_burned': float(shares), 'new_balance': float(user.userprofile.balance)})
        
    except Position.DoesNotExist:
        return JsonResponse({'message': 'No position in winning outcome.', 'payout': 0})


@csrf_exempt
def delete_market(request, slug):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=401)

    market = get_object_or_404(Market, slug=slug)

    # Allow staff/superusers to delete any market
    is_admin = request.user.is_staff or request.user.is_superuser
    if market.created_by != request.user and not is_admin:
        return JsonResponse({'error': 'Permission denied. You are not the owner.'}, status=403)

    market.delete()
    return JsonResponse({'message': 'Market deleted successfully.'}, status=200)


def user_portfolio(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=401)

    user = request.user
    
    # 1. Get Positions
    positions = Position.objects.filter(user=user).select_related('outcome', 'outcome__market')
    positions_data = []
    total_value = Decimal('0.0')

    for pos in positions:
        # Calculate current value based on outcome price
        # Value = Shares * Current Price
        current_value = pos.shares * pos.outcome.current_price
        total_value += current_value
        
        positions_data.append({
            'id': pos.id,
            'market_title': pos.outcome.market.title,
            'market_slug': pos.outcome.market.slug,
            'outcome_name': pos.outcome.name,
            'shares': pos.shares,
            'current_price': pos.outcome.current_price,
            'value': current_value
        })

    # 2. Get Created Markets
    created_markets = Market.objects.filter(created_by=user).order_by('-created_at')
    markets_data = [
        {
            'id': m.id,
            'title': m.title,
            'slug': m.slug,
            'status': m.status,
            'created_at': m.created_at.isoformat(),
        }
        for m in created_markets
    ]

    return JsonResponse({
        'positions': positions_data,
        'created_markets': markets_data,
        'total_value': total_value,
        'username': user.username,
        'balance': float(user.userprofile.balance)
    })


def market_ledger(request, slug):
    """
    Returns all positions for a market (public trading ledger).
    Shows who bet on what and how much.
    """
    market = get_object_or_404(Market, slug=slug)
    
    # Get all positions for all outcomes of this market
    positions = Position.objects.filter(
        outcome__market=market,
        shares__gt=0  # Only show positions with shares
    ).select_related('user', 'outcome').order_by('-shares')
    
    ledger = []
    for pos in positions:
        ledger.append({
            'username': pos.user.username,
            'outcome': pos.outcome.name,
            'shares': float(pos.shares),
            'value': float(pos.shares * pos.outcome.current_price),
        })

    trades = market.trades.select_related('user', 'outcome').all()[:100]
    trade_history = [
        {
            'id': trade.id,
            'username': trade.user.username,
            'outcome': trade.outcome.name,
            'amount': float(trade.amount),
            'shares': float(trade.shares),
            'price_before': float(trade.price_before),
            'price_after': float(trade.price_after),
            'created_at': trade.created_at.isoformat(),
        }
        for trade in trades
    ]
    
    return JsonResponse({
        'market': market.title,
        'ledger': ledger,
        'trades': trade_history,
        'total_bettors': len(set(pos.user_id for pos in positions)),
    })


@csrf_exempt
def market_comments(request, slug):
    """
    GET: Returns all comments for a market.
    POST: Adds a new comment to a market (requires auth).
    """
    market = get_object_or_404(Market, slug=slug)
    
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required.'}, status=401)
        
        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON body.'}, status=400)
        
        text = (payload.get('text') or '').strip()
        if not text:
            return JsonResponse({'error': 'Comment text is required.'}, status=400)
        if len(text) > 1000:
            return JsonResponse({'error': 'Comment too long (max 1000 chars).'}, status=400)
        
        comment = Comment.objects.create(
            market=market,
            user=request.user,
            text=text
        )
        
        return JsonResponse({
            'id': comment.id,
            'username': comment.user.username,
            'text': comment.text,
            'created_at': comment.created_at.isoformat(),
        }, status=201)
    
    # GET: Return all comments for this market
    comments = market.comments.select_related('user').all()[:50]  # Limit to 50 comments
    
    comments_data = [
        {
            'id': c.id,
            'username': c.user.username,
            'text': c.text,
            'created_at': c.created_at.isoformat(),
        }
        for c in comments
    ]
    
    return JsonResponse({
        'market': market.title,
        'comments': comments_data,
        'count': len(comments_data),
    })
