import json
from decimal import Decimal

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from .models import Market, Outcome, Position
from .services import CPMMService


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

        response_payload = {
            'id': market.id,
            'title': market.title,
            'slug': market.slug,
            'description': market.description,
            'status': market.status,
            'created_at': market.created_at.isoformat(),
            'created_by': market.created_by.username if market.created_by else None,
            'outcomes': [
                {
                    'id': o.id,
                    'name': o.name,
                    'price': o.current_price,
                    'pool': o.pool_balance,
                }
                for o in market.outcomes.all()
            ]
        }
        return JsonResponse(response_payload, status=201)

    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    markets = Market.objects.all()
    payload = [
        {
            'id': market.id,
            'title': market.title,
            'slug': market.slug,
            'description': market.description,
            'status': market.status,
            'created_at': market.created_at.isoformat(),
            'outcomes': [
                {
                    'id': o.id,
                    'name': o.name,
                    'price': o.current_price,
                    'pool': o.pool_balance,
                }
                for o in market.outcomes.all()
            ]
        }
        for market in markets
    ]
    return JsonResponse(payload, safe=False)


@csrf_exempt
def market_detail(request, slug):
    market = get_object_or_404(Market, slug=slug)

    if request.method in ['PUT', 'PATCH']:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required.'}, status=401)
        
        if market.created_by != request.user:
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

    payload = {
        'id': market.id,
        'title': market.title,
        'slug': market.slug,
        'description': market.description,
        'status': market.status,
        'created_at': market.created_at.isoformat(),
        'created_by': market.created_by.username if market.created_by else None,
        'outcomes': [
            {
                'id': o.id,
                'name': o.name,
                'price': o.current_price,
                'pool': o.pool_balance,
            }
            for o in market.outcomes.all()
        ]
    }
    return JsonResponse(payload)

from .services import CPMMService
from django.contrib.auth.models import User  # For demo, using first user or auth

@csrf_exempt
def trade_market(request, slug):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    market = get_object_or_404(Market, slug=slug)
    
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
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

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
    
    # In a real app, check for request.user.is_staff or similar
    
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
        
        return JsonResponse({'status': 'redeemed', 'payout': payout, 'shares_burned': float(shares)})
        
    except Position.DoesNotExist:
        return JsonResponse({'message': 'No position in winning outcome.', 'payout': 0})


@csrf_exempt
def delete_market(request, slug):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=401)

    market = get_object_or_404(Market, slug=slug)

    if market.created_by != request.user:
        return JsonResponse({'error': 'Permission denied. You are not the owner.'}, status=403)

    market.delete()
    return JsonResponse({'message': 'Market deleted successfully.'}, status=200)
