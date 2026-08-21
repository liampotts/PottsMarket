import hashlib
import json
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt

from .claimlab import ClaimLabError, canonical_youtube_url, extract_youtube_id
from .models import Claim, Document, Evidence, ForecastSnapshot, Market, Source
from .services import CPMMService
from .tasks import process_source


def _json_payload(request):
    try:
        return json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError as error:
        raise ClaimLabError('Invalid JSON body.') from error


def _has_claim_lab_access(user):
    if not settings.CLAIM_LAB_ENABLED or not user.is_authenticated:
        return False
    return (
        user.is_staff
        or user.is_superuser
        or user.groups.filter(name=settings.CLAIM_LAB_GROUP).exists()
    )


def _require_access(request):
    if not settings.CLAIM_LAB_ENABLED:
        return JsonResponse({'error': 'Claim Lab is not enabled.'}, status=404)
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=401)
    if not _has_claim_lab_access(request.user):
        return JsonResponse({'error': 'Claim Lab invitation required.'}, status=403)
    return None


def _serialize_evidence(item):
    return {
        'id': item.id,
        'title': item.title,
        'url': item.url,
        'excerpt': item.excerpt,
        'stance': item.stance,
        'published_at': item.published_at.isoformat() if item.published_at else None,
        'captured_at': item.captured_at.isoformat(),
    }


def _serialize_claim(claim):
    return {
        'id': claim.id,
        'statement': claim.statement,
        'excerpt': claim.excerpt,
        'excerpt_start_seconds': claim.excerpt_start_seconds,
        'rationale': claim.rationale,
        'resolution_criteria': claim.resolution_criteria,
        'resolution_source_url': claim.resolution_source_url,
        'closes_at': claim.closes_at.isoformat(),
        'resolves_at': claim.resolves_at.isoformat(),
        'confidence': float(claim.confidence),
        'extraction_method': claim.extraction_method,
        'status': claim.status,
        'market': {
            'id': claim.market.id,
            'slug': claim.market.slug,
            'status': claim.market.status,
        } if claim.market else None,
        'evidence': [_serialize_evidence(item) for item in claim.evidence.all()],
    }


def _serialize_source(source, include_claims=True):
    claims = []
    if include_claims and hasattr(source, 'document'):
        claims = [_serialize_claim(claim) for claim in source.document.claims.all()]
    public_metadata = {
        key: value
        for key, value in (source.metadata or {}).items()
        if key not in {'editorial_transcript', 'editorial_title'}
    }
    return {
        'id': source.id,
        'source_type': source.source_type,
        'url': source.url,
        'external_id': source.external_id,
        'title': source.title,
        'author': source.author,
        'status': source.status,
        'error': source.error,
        'metadata': public_metadata,
        'created_by': source.created_by.username,
        'created_at': source.created_at.isoformat(),
        'processed_at': source.processed_at.isoformat() if source.processed_at else None,
        'claim_count': len(claims),
        'claims': claims,
    }


def _parse_required_datetime(value, field, errors):
    parsed = parse_datetime(str(value or ''))
    if parsed is None:
        errors[field] = 'Use an ISO-8601 timestamp.'
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _claim_values(payload, existing=None):
    errors = {}
    statement = str(payload.get('statement', getattr(existing, 'statement', ''))).strip()
    criteria = str(
        payload.get('resolution_criteria', getattr(existing, 'resolution_criteria', ''))
    ).strip()
    source_url = str(
        payload.get('resolution_source_url', getattr(existing, 'resolution_source_url', ''))
    ).strip()
    closes_at = _parse_required_datetime(
        payload.get('closes_at', getattr(existing, 'closes_at', '')),
        'closes_at',
        errors,
    )
    resolves_at = _parse_required_datetime(
        payload.get('resolves_at', getattr(existing, 'resolves_at', '')),
        'resolves_at',
        errors,
    )

    if len(statement) < 15:
        errors['statement'] = 'Use a specific binary question of at least 15 characters.'
    if len(criteria) < 30:
        errors['resolution_criteria'] = 'Define an objective YES/NO resolution rule.'
    if not source_url.startswith(('https://', 'http://')):
        errors['resolution_source_url'] = 'Use a public HTTP(S) resolution source.'
    if closes_at and resolves_at and resolves_at <= closes_at:
        errors['resolves_at'] = 'Resolution must happen after trading closes.'

    try:
        confidence = Decimal(str(payload.get('confidence', getattr(existing, 'confidence', 0.5))))
        if not Decimal('0') <= confidence <= Decimal('1'):
            raise InvalidOperation
    except (InvalidOperation, TypeError, ValueError):
        confidence = Decimal('0.5')
        errors['confidence'] = 'Confidence must be between 0 and 1.'

    if errors:
        raise ClaimLabError(json.dumps(errors))

    try:
        excerpt_start = payload.get(
            'excerpt_start_seconds',
            getattr(existing, 'excerpt_start_seconds', None),
        )
        excerpt_start = int(excerpt_start) if excerpt_start not in (None, '') else None
    except (TypeError, ValueError):
        excerpt_start = None

    return {
        'statement': statement[:500],
        'excerpt': str(payload.get('excerpt', getattr(existing, 'excerpt', ''))).strip()[:2000],
        'excerpt_start_seconds': excerpt_start,
        'rationale': str(payload.get('rationale', getattr(existing, 'rationale', ''))).strip()[:3000],
        'resolution_criteria': criteria[:5000],
        'resolution_source_url': source_url[:1000],
        'closes_at': closes_at,
        'resolves_at': resolves_at,
        'confidence': confidence,
    }


def claim_lab_config(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)
    return JsonResponse({
        'enabled': settings.CLAIM_LAB_ENABLED,
        'can_access': _has_claim_lab_access(request.user),
        'model': settings.CLAIM_LLM_MODEL,
        'llm_configured': bool(settings.CLAIM_LLM_BASE_URL),
    })


@csrf_exempt
def source_list(request):
    access_error = _require_access(request)
    if access_error:
        return access_error

    if request.method == 'GET':
        sources = Source.objects.select_related('created_by', 'document').prefetch_related(
            'document__claims__market',
            'document__claims__evidence',
        )[:50]
        return JsonResponse({'sources': [_serialize_source(source) for source in sources]})

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    try:
        payload = _json_payload(request)
        video_id = extract_youtube_id(payload.get('url'))
        url = canonical_youtube_url(video_id)
    except ClaimLabError as error:
        return JsonResponse({'error': str(error)}, status=400)

    source = Source.objects.filter(url=url).first()
    created = False
    if source is None:
        try:
            source = Source.objects.create(
                source_type=Source.TYPE_YOUTUBE,
                url=url,
                external_id=video_id,
                created_by=request.user,
            )
            created = True
        except IntegrityError:
            source = Source.objects.get(url=url)

    if source.status in {Source.STATUS_FAILED, Source.STATUS_NEEDS_REVIEW}:
        source.status = Source.STATUS_QUEUED
        source.error = ''
        source.save(update_fields=['status', 'error'])

    if created or source.status == Source.STATUS_QUEUED:
        try:
            process_source.delay(source.id)
        except Exception as error:
            source.status = Source.STATUS_FAILED
            source.error = f'Could not queue ingestion: {error}'
            source.save(update_fields=['status', 'error'])
            return JsonResponse({'error': source.error}, status=503)

    source.refresh_from_db()
    return JsonResponse(_serialize_source(source), status=201 if created else 200)


def source_detail(request, source_id):
    access_error = _require_access(request)
    if access_error:
        return access_error
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    source = get_object_or_404(
        Source.objects.select_related('created_by', 'document').prefetch_related(
            'document__claims__market',
            'document__claims__evidence',
        ),
        pk=source_id,
    )
    return JsonResponse(_serialize_source(source))


@csrf_exempt
def source_retry(request, source_id):
    access_error = _require_access(request)
    if access_error:
        return access_error
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    source = get_object_or_404(Source, pk=source_id)
    source.status = Source.STATUS_QUEUED
    source.error = ''
    source.save(update_fields=['status', 'error'])
    try:
        process_source.delay(source.id)
    except Exception as error:
        source.status = Source.STATUS_FAILED
        source.error = f'Could not queue ingestion: {error}'
        source.save(update_fields=['status', 'error'])
        return JsonResponse({'error': source.error}, status=503)
    return JsonResponse({'status': 'queued', 'source_id': source.id})


@csrf_exempt
def source_transcript(request, source_id):
    access_error = _require_access(request)
    if access_error:
        return access_error
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    source = get_object_or_404(Source, pk=source_id)
    if source.status in {Source.STATUS_QUEUED, Source.STATUS_PROCESSING}:
        return JsonResponse({'error': 'Wait for the current ingestion job to finish.'}, status=409)

    try:
        payload = _json_payload(request)
        transcript = str(payload.get('transcript') or '').strip()
        title = str(payload.get('title') or '').strip()
        if len(transcript) < 80:
            raise ClaimLabError('Paste at least 80 characters of transcript text.')
        if len(transcript) > 200_000:
            raise ClaimLabError('Transcript text must be 200,000 characters or fewer.')
    except ClaimLabError as error:
        return JsonResponse({'error': str(error)}, status=400)

    source.metadata = {
        **(source.metadata or {}),
        'editorial_transcript': transcript,
        'editorial_title': title[:500],
    }
    source.status = Source.STATUS_QUEUED
    source.error = ''
    source.save(update_fields=['metadata', 'status', 'error'])
    try:
        process_source.delay(source.id)
    except Exception as error:
        source.status = Source.STATUS_FAILED
        source.error = f'Could not queue transcript ingestion: {error}'
        source.save(update_fields=['status', 'error'])
        return JsonResponse({'error': source.error}, status=503)
    return JsonResponse({'status': 'queued', 'source_id': source.id})


@csrf_exempt
def source_claims(request, source_id):
    access_error = _require_access(request)
    if access_error:
        return access_error
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    source = get_object_or_404(Source, pk=source_id)
    if not hasattr(source, 'document'):
        return JsonResponse({'error': 'The source has no transcript document yet.'}, status=400)
    try:
        values = _claim_values(_json_payload(request))
    except ClaimLabError as error:
        try:
            errors = json.loads(str(error))
        except json.JSONDecodeError:
            errors = {'form': str(error)}
        return JsonResponse({'errors': errors}, status=400)

    claim = Claim.objects.create(
        document=source.document,
        extraction_method='manual',
        **values,
    )
    return JsonResponse(_serialize_claim(claim), status=201)


@csrf_exempt
def claim_detail(request, claim_id):
    access_error = _require_access(request)
    if access_error:
        return access_error
    if request.method != 'PATCH':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    claim = get_object_or_404(Claim.objects.prefetch_related('evidence'), pk=claim_id)
    if claim.status == Claim.STATUS_PUBLISHED:
        return JsonResponse({'error': 'Published claims are immutable.'}, status=400)
    try:
        payload = _json_payload(request)
        values = _claim_values(payload, existing=claim)
    except ClaimLabError as error:
        try:
            errors = json.loads(str(error))
        except json.JSONDecodeError:
            errors = {'form': str(error)}
        return JsonResponse({'errors': errors}, status=400)

    requested_status = payload.get('status', claim.status)
    if requested_status not in {Claim.STATUS_SUGGESTED, Claim.STATUS_APPROVED, Claim.STATUS_REJECTED}:
        return JsonResponse({'error': 'Invalid claim status.'}, status=400)

    for field, value in values.items():
        setattr(claim, field, value)
    claim.status = requested_status
    if requested_status in {Claim.STATUS_APPROVED, Claim.STATUS_REJECTED}:
        claim.reviewed_by = request.user
        claim.reviewed_at = timezone.now()
    claim.save()
    return JsonResponse(_serialize_claim(claim))


@csrf_exempt
def claim_publish(request, claim_id):
    access_error = _require_access(request)
    if access_error:
        return access_error
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    with transaction.atomic():
        claim = get_object_or_404(
            Claim.objects.select_for_update().select_related('document__source', 'market'),
            pk=claim_id,
        )
        if claim.status != Claim.STATUS_APPROVED:
            return JsonResponse({'error': 'Approve the claim before publishing.'}, status=400)
        if claim.market:
            return JsonResponse({'error': 'This claim is already published.'}, status=400)

        slug_root = slugify(claim.statement)[:175] or f'claim-{claim.id}'
        slug = f'{slug_root}-{claim.id}'
        description = (
            f'{claim.rationale}\n\nResolution criteria: {claim.resolution_criteria}'
        ).strip()
        market = Market.objects.create(
            title=claim.statement,
            slug=slug,
            description=description,
            status=Market.STATUS_OPEN,
            created_by=claim.document.source.created_by,
        )
        CPMMService.initialize_market(market)
        claim.market = market
        claim.status = Claim.STATUS_PUBLISHED
        claim.reviewed_by = request.user
        claim.reviewed_at = timezone.now()
        claim.save(update_fields=['market', 'status', 'reviewed_by', 'reviewed_at'])

        evidence_hash = hashlib.sha256(claim.excerpt.encode('utf-8')).hexdigest() if claim.excerpt else ''
        Evidence.objects.get_or_create(
            claim=claim,
            url=claim.document.source.url,
            defaults={
                'title': claim.document.source.title,
                'excerpt': claim.excerpt,
                'stance': Evidence.STANCE_CONTEXT,
                'content_hash': evidence_hash,
            },
        )
        ForecastSnapshot.objects.create(
            market=market,
            agent_name=settings.CLAIM_LLM_MODEL,
            probability=Decimal('0.5000'),
            rationale='Neutral prior recorded when the source-backed market was published.',
        )

    return JsonResponse({
        'status': 'published',
        'market': {'id': market.id, 'slug': market.slug, 'title': market.title},
        'claim': _serialize_claim(claim),
    }, status=201)
