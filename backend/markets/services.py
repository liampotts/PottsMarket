from decimal import Decimal
import math
from django.db import transaction
from django.contrib.auth.models import User
from .models import Market, Outcome, Position

class CPMMService:
    @staticmethod
    def initialize_market(market: Market, liquidity: Decimal = Decimal('100.0')):
        """
        Initialize market outcomes with equal liquidity (50/50 probability).
        Creates YES and NO outcomes if they don't exist.
        """
        # Create YES and NO outcomes
        yes, _ = Outcome.objects.get_or_create(
            market=market, 
            name="YES",
            defaults={'current_price': 0.5, 'pool_balance': liquidity}
        )
        no, _ = Outcome.objects.get_or_create(
            market=market, 
            name="NO",
            defaults={'current_price': 0.5, 'pool_balance': liquidity}
        )
        
        # Ensure balances are set (in case they existed but were different)
        # For this demo, strictly resetting or ensuring initialization
        if yes.pool_balance == 0:
            yes.pool_balance = liquidity
            yes.save()
        if no.pool_balance == 0:
            no.pool_balance = liquidity
            no.save()
            
        return yes, no

    @staticmethod
    def get_price(outcome: Outcome) -> Decimal:
        """
        Calculate price of an outcome based on pool balances.
        Price(Yes) = R_no / (R_yes + R_no) in simple probability terms?
        Actually for CPMM:
        Implicit Probability = Pool_Other / (Pool_Yes + Pool_Other)
        """
        market_outcomes = outcome.market.outcomes.all()
        if market_outcomes.count() < 2:
            return Decimal('0.5')
            
        # Assuming binary market for now
        this_balance = outcome.pool_balance
        other_balance = sum(o.pool_balance for o in market_outcomes if o != outcome)
        
        if this_balance + other_balance == 0:
            return Decimal('0.5')
            
        return Decimal(other_balance) / Decimal(this_balance + other_balance)

    @staticmethod
    @transaction.atomic
    def buy_tokens(user: User, outcome: Outcome, investment_amount: Decimal):
        """
        Executes a buy order using CPMM logic (Gnosis style).
        1. User invests 'investment_amount' (USD).
        2. This amount is conceptually 'split' into equal YES and NO shares.
        3. The shares of the OTHER outcome are sold to the pool to buy more of the DESIRED outcome.
        
        Result: User gets (Investment + Bought Shares) of the DESIRED outcome.
        Price of Desired Outcome goes UP.
        """
        market = outcome.market
        # Get all outcomes (assume binary YES/NO)
        all_outcomes = list(market.outcomes.all())
        other_outcome = next(o for o in all_outcomes if o != outcome)
        
        # 1. State before trade
        R_yes = outcome.pool_balance
        R_no = other_outcome.pool_balance
        k = R_yes * R_no
        
        # 2. Add investment to pool (conceptually user splits investment -> YES + NO)
        # We add 'investment' to the NO pool (because we are selling the NO part)
        # The pool now has (R_no + investment).
        new_R_no = R_no + investment_amount
        
        # 3. Calculate new R_yes to maintain k
        # new_R_yes * new_R_no = k
        new_R_yes = k / new_R_no
        
        # 4. Shares bought = Old R_yes - New R_yes
        shares_bought_from_pool = R_yes - new_R_yes
        
        # Total shares user receives = investment (from split) + shares_bought_from_pool
        total_shares = investment_amount + shares_bought_from_pool
        
        # 5. Update Pools
        outcome.pool_balance = new_R_yes
        other_outcome.pool_balance = new_R_no
        
        # Update prices
        outcome.current_price = CPMMService.get_price(outcome)
        other_outcome.current_price = CPMMService.get_price(other_outcome)
        
        outcome.save()
        other_outcome.save()
        
        # 6. Create/Update User Position
        position, _ = Position.objects.get_or_create(user=user, outcome=outcome)
        position.shares = Decimal(str(position.shares)) + total_shares
        position.save()
        
        return {
            'shares_bought': total_shares,
            'new_price': outcome.current_price,
            'avg_price': investment_amount / total_shares if total_shares > 0 else 0
        }
