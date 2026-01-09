from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from .models import Market


def market_list(request):
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
