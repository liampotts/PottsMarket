import json

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

# Create your views here.
