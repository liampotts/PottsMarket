from decimal import Decimal
from datetime import timedelta
import json
from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.utils import timezone
from .claimlab import ClaimLabError, extract_youtube_id
from .models import Claim, Document, Market, Outcome, Position, Source, Trade
from .services import CPMMService
from .tasks import process_source

class MarketTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test_user', password='test-password-123')
        self.market = Market.objects.create(
            title="Will it rain?",
            slug="will-it-rain",
            description="Weather market",
            status=Market.STATUS_OPEN,
            created_by=self.user,
        )
        self.client = Client()

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_health_check(self):
        response = self.client.get('/api/health/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_initialization(self):
        """Test that market initializes with 50/50 prices."""
        yes, no = CPMMService.initialize_market(self.market)
        
        self.assertEqual(yes.pool_balance, Decimal('100.0'))
        self.assertEqual(no.pool_balance, Decimal('100.0'))
        self.assertEqual(yes.current_price, 0.5)
        self.assertEqual(no.current_price, 0.5)

    def test_trading_logic(self):
        """Test buying YES shares increases price."""
        yes, no = CPMMService.initialize_market(self.market)
        
        # Buy $10 of YES
        # Original Pools: 100, 100. k = 10000.
        # Add 10 to NO pool -> 110.
        # New YES pool = 10000 / 110 = 90.9090...
        # Bought YES = 100 - 90.9090 = 9.0909...
        # Total YES shares = 10 (split) + 9.0909 = 19.09...
        
        result = CPMMService.buy_tokens(self.user, yes, Decimal('10.0'))
        
        yes.refresh_from_db()
        no.refresh_from_db()
        
        # Price of YES should be > 0.50
        # Price Yes = Pool No / (Pool Yes + Pool No)
        # Price Yes = 110 / (90.90 + 110) = 110 / 200.90 = ~0.547
        self.assertGreater(yes.current_price, Decimal('0.50'))
        self.assertLess(no.current_price, Decimal('0.50'))
        
        # User should have position
        pos = Position.objects.get(user=self.user, outcome=yes)
        self.assertGreater(pos.shares, 0)

    def test_trade_endpoint(self):
        """Authenticated trades update both the position and cash balance."""
        data = {
            'outcome_id': 0, # Placeholder
            'amount': 20,
        }
        
        # Need to init market first to get IDs
        yes, no = CPMMService.initialize_market(self.market)
        data['outcome_id'] = yes.id
        
        unauthenticated_response = self.client.post(
            f'/api/markets/{self.market.slug}/trade/',
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(unauthenticated_response.status_code, 401)

        self.client.force_login(self.user)
        response = self.client.post(
            f'/api/markets/{self.market.slug}/trade/',
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        json_resp = response.json()
        self.assertEqual(json_resp['status'], 'success')
        self.assertTrue(float(json_resp['trade']['shares_bought']) > 0)

        self.user.userprofile.refresh_from_db()
        self.assertEqual(self.user.userprofile.balance, Decimal('980.00'))
        trade = Trade.objects.get(user=self.user, market=self.market)
        self.assertEqual(trade.amount, Decimal('20.0000'))
        self.assertGreater(trade.shares, Decimal('20.0000'))

    def test_only_owner_or_admin_can_resolve_market(self):
        """Resolution cannot be triggered anonymously or by another user."""
        yes, _ = CPMMService.initialize_market(self.market)
        url = f'/api/markets/{self.market.slug}/resolve/'
        data = json.dumps({'outcome_id': yes.id})

        self.assertEqual(
            self.client.post(url, data=data, content_type='application/json').status_code,
            401,
        )

        other_user = User.objects.create_user(username='other-user', password='password-123')
        self.client.force_login(other_user)
        self.assertEqual(
            self.client.post(url, data=data, content_type='application/json').status_code,
            403,
        )

        self.client.force_login(self.user)
        response = self.client.post(url, data=data, content_type='application/json')
        self.assertEqual(response.status_code, 200)

        self.market.refresh_from_db()
        self.assertEqual(self.market.status, Market.STATUS_RESOLVED)
        self.assertEqual(self.market.winning_outcome, yes)

    def test_closed_market_rejects_trades(self):
        yes, _ = CPMMService.initialize_market(self.market)
        self.market.status = Market.STATUS_RESOLVED
        self.market.winning_outcome = yes
        self.market.save()
        self.client.force_login(self.user)

        response = self.client.post(
            f'/api/markets/{self.market.slug}/trade/',
            data=json.dumps({'outcome_id': yes.id, 'amount': 20}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'This market is not open for trading.')


@override_settings(CLAIM_LAB_ENABLED=True, CLAIM_LAB_GROUP='claim-lab')
class ClaimLabTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username='claim-editor',
            password='test-password-123',
            is_staff=True,
        )
        self.member = User.objects.create_user(
            username='ordinary-user',
            password='test-password-123',
        )
        self.client = Client()

    def _create_processed_source(self):
        source = Source.objects.create(
            source_type=Source.TYPE_YOUTUBE,
            url='https://www.youtube.com/watch?v=abcdefghijk',
            external_id='abcdefghijk',
            title='A model release forecast',
            author='Test channel',
            status=Source.STATUS_READY,
            created_by=self.staff,
        )
        document = Document.objects.create(
            source=source,
            content='The team will release the model next year.',
            language='en',
            content_hash='a' * 64,
            segments=[{'text': 'The team will release the model next year.', 'start': 12}],
        )
        now = timezone.now()
        claim = Claim.objects.create(
            document=document,
            statement='Will the team release the model before next year ends?',
            excerpt='The team will release the model next year.',
            excerpt_start_seconds=12,
            rationale='A concrete release prediction.',
            resolution_criteria='Resolve YES if the official release is publicly available before the deadline; otherwise NO.',
            resolution_source_url='https://example.com/releases',
            closes_at=now + timedelta(days=14),
            resolves_at=now + timedelta(days=90),
            confidence=Decimal('0.900'),
            extraction_method='llm:test-model',
        )
        return source, claim

    def test_youtube_url_parser_accepts_common_urls(self):
        self.assertEqual(
            extract_youtube_id('https://www.youtube.com/watch?v=abcdefghijk'),
            'abcdefghijk',
        )
        self.assertEqual(
            extract_youtube_id('https://youtu.be/abcdefghijk?t=10'),
            'abcdefghijk',
        )
        with self.assertRaises(ClaimLabError):
            extract_youtube_id('https://example.com/watch?v=abcdefghijk')

    def test_claim_lab_requires_an_invitation(self):
        self.client.force_login(self.member)
        response = self.client.get('/api/claim-lab/sources/')
        self.assertEqual(response.status_code, 403)

        config = self.client.get('/api/claim-lab/config/').json()
        self.assertTrue(config['enabled'])
        self.assertFalse(config['can_access'])

    @patch('markets.claimlab_views.process_source.delay')
    def test_staff_can_submit_a_source_for_background_processing(self, delay):
        self.client.force_login(self.staff)
        response = self.client.post(
            '/api/claim-lab/sources/',
            data=json.dumps({'url': 'https://youtu.be/abcdefghijk?t=10'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        source = Source.objects.get()
        self.assertEqual(source.url, 'https://www.youtube.com/watch?v=abcdefghijk')
        self.assertEqual(response.json()['status'], Source.STATUS_QUEUED)
        delay.assert_called_once_with(source.id)

    @patch('markets.claimlab_views.process_source.delay')
    def test_staff_can_supply_a_transcript_after_automated_fetch_fails(self, delay):
        source = Source.objects.create(
            source_type=Source.TYPE_YOUTUBE,
            url='https://www.youtube.com/watch?v=abcdefghijk',
            external_id='abcdefghijk',
            status=Source.STATUS_FAILED,
            error='YouTube blocked transcript discovery.',
            created_by=self.staff,
        )
        transcript = (
            'The team expects to release a public model next year. '
            'The launch will be documented on the official releases page. '
            'This editorial transcript is long enough for ingestion.'
        )
        self.client.force_login(self.staff)

        response = self.client.post(
            f'/api/claim-lab/sources/{source.id}/transcript/',
            data=json.dumps({'title': 'Editorial source', 'transcript': transcript}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        source.refresh_from_db()
        self.assertEqual(source.status, Source.STATUS_QUEUED)
        self.assertEqual(source.metadata['editorial_transcript'], transcript)
        delay.assert_called_once_with(source.id)

        detail = self.client.get(f'/api/claim-lab/sources/{source.id}/').json()
        self.assertNotIn('editorial_transcript', detail['metadata'])

    @patch('markets.tasks.extract_claim_candidates')
    @patch('markets.tasks.fetch_youtube_document')
    def test_worker_persists_transcript_and_claims(self, fetch_document, extract_claims):
        source = Source.objects.create(
            source_type=Source.TYPE_YOUTUBE,
            url='https://www.youtube.com/watch?v=abcdefghijk',
            external_id='abcdefghijk',
            created_by=self.staff,
        )
        fetch_document.return_value = {
            'external_id': 'abcdefghijk',
            'canonical_url': source.url,
            'title': 'The next model release',
            'author': 'Test channel',
            'metadata': {'provider_name': 'YouTube'},
            'language': 'en',
            'segments': [{'text': 'A new model will launch next year.', 'start': 4}],
            'content': 'A new model will launch next year.',
            'content_hash': 'b' * 64,
        }
        now = timezone.now()
        extract_claims.return_value = ([{
            'statement': 'Will a new model launch before next year ends?',
            'excerpt': 'A new model will launch next year.',
            'excerpt_start_seconds': 4,
            'rationale': 'This is a dated launch prediction.',
            'resolution_criteria': 'Resolve YES if the official model is publicly released before the deadline; otherwise NO.',
            'resolution_source_url': 'https://example.com/releases',
            'closes_at': now + timedelta(days=14),
            'resolves_at': now + timedelta(days=90),
            'confidence': 0.85,
            'extraction_method': 'llm:test-model',
        }], '')

        result = process_source(source.id)

        source.refresh_from_db()
        self.assertEqual(result['status'], Source.STATUS_READY)
        self.assertEqual(source.title, 'The next model release')
        self.assertEqual(source.document.claims.count(), 1)

    @patch('markets.tasks.extract_claim_candidates')
    @patch('markets.tasks.build_editorial_youtube_document')
    @patch('markets.tasks.fetch_youtube_document')
    def test_worker_uses_supplied_transcript_when_present(
        self,
        fetch_document,
        build_editorial_document,
        extract_claims,
    ):
        transcript = (
            'The team expects to release a public model next year. '
            'The launch will be documented on the official releases page.'
        )
        source = Source.objects.create(
            source_type=Source.TYPE_YOUTUBE,
            url='https://www.youtube.com/watch?v=abcdefghijk',
            external_id='abcdefghijk',
            created_by=self.staff,
            metadata={'editorial_transcript': transcript, 'editorial_title': 'Release forecast'},
        )
        build_editorial_document.return_value = {
            'external_id': 'abcdefghijk',
            'canonical_url': source.url,
            'title': 'Release forecast',
            'author': 'Editorial channel',
            'metadata': {'transcript_source': 'editorial'},
            'language': 'en',
            'segments': [{'text': transcript, 'start': None}],
            'content': transcript,
            'content_hash': 'c' * 64,
        }
        extract_claims.return_value = ([], '')

        result = process_source(source.id)

        source.refresh_from_db()
        self.assertEqual(result['status'], Source.STATUS_NEEDS_REVIEW)
        self.assertEqual(source.document.content, transcript)
        self.assertEqual(source.metadata['transcript_source'], 'editorial')
        self.assertNotIn('editorial_transcript', source.metadata)
        fetch_document.assert_not_called()

    def test_approved_claim_publishes_an_auditable_market(self):
        source, claim = self._create_processed_source()
        self.client.force_login(self.staff)

        review = self.client.patch(
            f'/api/claim-lab/claims/{claim.id}/',
            data=json.dumps({'status': Claim.STATUS_APPROVED}),
            content_type='application/json',
        )
        self.assertEqual(review.status_code, 200)
        self.assertEqual(review.json()['status'], Claim.STATUS_APPROVED)

        publish = self.client.post(f'/api/claim-lab/claims/{claim.id}/publish/')
        self.assertEqual(publish.status_code, 201)

        claim.refresh_from_db()
        self.assertEqual(claim.status, Claim.STATUS_PUBLISHED)
        self.assertEqual(claim.market.status, Market.STATUS_OPEN)
        self.assertEqual(claim.market.outcomes.count(), 2)
        self.assertEqual(claim.market.forecasts.count(), 1)
        self.assertEqual(claim.evidence.count(), 1)

        feed = self.client.get('/api/markets/').json()
        published = next(item for item in feed if item['id'] == claim.market_id)
        self.assertEqual(published['source']['url'], source.url)
        self.assertIn('official release', published['source']['resolution_criteria'])

    def test_manual_claim_creation_supports_transcripts_with_no_candidates(self):
        source, _ = self._create_processed_source()
        source.document.claims.all().delete()
        self.client.force_login(self.staff)
        now = timezone.now()

        response = self.client.post(
            f'/api/claim-lab/sources/{source.id}/claims/',
            data=json.dumps({
                'statement': 'Will the project publish a stable release this quarter?',
                'excerpt': 'We plan to publish this quarter.',
                'resolution_criteria': 'Resolve YES if the stable release appears on the official releases page by the deadline; otherwise NO.',
                'resolution_source_url': 'https://example.com/releases',
                'closes_at': (now + timedelta(days=7)).isoformat(),
                'resolves_at': (now + timedelta(days=60)).isoformat(),
                'confidence': 1,
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['extraction_method'], 'manual')
