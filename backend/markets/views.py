import json
from decimal import Decimal

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from .models import Market


@csrf_exempt
def market_list(request):
    if request.method == 'POST':
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
        )

        response_payload = {
            'id': market.id,
            'title': market.title,
            'slug': market.slug,
            'description': market.description,
            'status': market.status,
            'created_at': market.created_at.isoformat(),
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
        }
        for market in markets
    ]
    return JsonResponse(payload, safe=False)


def market_detail(request, slug):
    market = get_object_or_404(Market, slug=slug)
    payload = {
        'id': market.id,
        'title': market.title,
        'slug': market.slug,
        'description': market.description,
        'status': market.status,
        'created_at': market.created_at.isoformat(),
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

    # For MVP DEMO: We will just assume User ID 1 exists or create a temp user
    # IN REAL APP: Use request.user and @login_required
    user_id = payload.get('user_id')
    if not user_id:
        # Auto-create a test user if none exists for easy testing
        user, _ = User.objects.get_or_create(username='test_trader')
    else:
        user = get_object_or_404(User, pk=user_id)

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

