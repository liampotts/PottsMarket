from decimal import Decimal
import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import Market, Outcome, Position
from .services import CPMMService

class MarketTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='test_user')
        self.market = Market.objects.create(
            title="Will it rain?",
            slug="will-it-rain",
            description="Weather market",
            status=Market.STATUS_OPEN
        )
        self.client = Client()

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
        """Test the API endpoint."""
        data = {
            'outcome_id': 0, # Placeholder
            'amount': 20,
            'user_id': self.user.id
        }
        
        # Need to init market first to get IDs
        yes, no = CPMMService.initialize_market(self.market)
        data['outcome_id'] = yes.id
        
        response = self.client.post(
            f'/api/markets/{self.market.slug}/trade/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        json_resp = response.json()
        self.assertEqual(json_resp['status'], 'success')
        self.assertTrue(float(json_resp['trade']['shares_bought']) > 0)
