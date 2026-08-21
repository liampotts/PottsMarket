from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .claimlab import (
    ClaimLabError,
    build_editorial_youtube_document,
    extract_claim_candidates,
    fetch_youtube_document,
)
from .models import Claim, Document, Source


@shared_task(bind=True, autoretry_for=(), max_retries=0)
def process_source(self, source_id):
    source = Source.objects.get(pk=source_id)
    source.status = Source.STATUS_PROCESSING
    source.error = ''
    source.save(update_fields=['status', 'error'])

    try:
        source_metadata = source.metadata or {}
        editorial_transcript = str(source_metadata.get('editorial_transcript') or '').strip()
        if editorial_transcript:
            fetched = build_editorial_youtube_document(
                source.url,
                editorial_transcript,
                source_metadata.get('editorial_title', ''),
            )
        else:
            fetched = fetch_youtube_document(source.url)
        candidates, llm_error = extract_claim_candidates(
            fetched['title'],
            fetched['canonical_url'],
            fetched['content'],
            fetched['segments'],
        )

        with transaction.atomic():
            source.external_id = fetched['external_id']
            source.url = fetched['canonical_url']
            source.title = fetched['title']
            source.author = fetched['author']
            source.metadata = {
                **fetched['metadata'],
                'llm_warning': llm_error,
            }
            source.processed_at = timezone.now()
            source.error = ''
            source.status = Source.STATUS_READY if candidates else Source.STATUS_NEEDS_REVIEW
            source.save()

            document, _ = Document.objects.update_or_create(
                source=source,
                defaults={
                    'content': fetched['content'],
                    'language': fetched['language'],
                    'content_hash': fetched['content_hash'],
                    'segments': fetched['segments'],
                },
            )
            document.claims.filter(status=Claim.STATUS_SUGGESTED, market__isnull=True).delete()
            Claim.objects.bulk_create([
                Claim(document=document, **candidate)
                for candidate in candidates
            ])
        return {'source_id': source.id, 'claims': len(candidates), 'status': source.status}
    except ClaimLabError as error:
        source.status = Source.STATUS_FAILED
        source.error = str(error)
        source.processed_at = timezone.now()
        source.save(update_fields=['status', 'error', 'processed_at'])
        return {'source_id': source.id, 'claims': 0, 'status': source.status, 'error': source.error}
    except Exception as error:
        source.status = Source.STATUS_FAILED
        source.error = f'Unexpected ingestion failure: {error}'
        source.processed_at = timezone.now()
        source.save(update_fields=['status', 'error', 'processed_at'])
        raise
