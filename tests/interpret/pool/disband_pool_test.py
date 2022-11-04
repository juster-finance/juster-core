from decimal import Decimal
from pytezos import MichelsonRuntimeError

from tests.interpret.pool.pool_base import PoolBaseTestCase


class DisbandPoolTestCase(PoolBaseTestCase):
    def test_should_set_disband_allow_if_manager_calls(self):
        self.disband(sender=self.manager)

    def test_should_fail_to_disband_if_not_manager_calls(self):
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.disband(sender=self.c)

        msg = 'Not a contract manager'
        self.assertTrue(msg in str(cm.exception))

    def test_should_allow_to_claim_others_liquidity_if_pool_in_disbanded_state(self):
        self.add_line()
        entry_id = self.deposit_liquidity(sender=self.a)
        provider = self.approve_liquidity(entry_id=entry_id)
        self.disband(sender=self.manager)
        self.claim_liquidity(sender=self.b, provider=provider)

        assert self.balances[self.a] == Decimal(0)

    def test_should_create_claims_for_disbanded_liquidity(self):
        # two events, 100 mutez liquidity, one event should have 50 mutez:
        line_id = self.add_line(max_events=2)
        entry_id = self.deposit_liquidity(sender=self.a, amount=100)
        provider = self.approve_liquidity(entry_id=entry_id)
        event_id = self.create_event(line_id=line_id)
        self.disband(sender=self.manager)
        self.claim_liquidity(sender=self.b, provider=provider, shares=100)

        assert len(self.storage['claims']) == 1
        assert self.balances[self.a] == Decimal(-50)

        self.pay_reward(event_id=event_id, amount=50)
        claims = [{'provider': provider, 'eventId': event_id}]
        amounts = self.withdraw_liquidity(claims=claims, sender=self.b)
        assert self.balances[self.a] == Decimal(0)

    def test_should_allow_to_cancel_others_liquidity_if_pool_in_disbanded_state(self):
        self.add_line()
        entry_id = self.deposit_liquidity(sender=self.a)
        self.trigger_pause_deposit(sender=self.manager)
        self.disband(sender=self.manager)
        self.cancel_liquidity(sender=self.b, entry_id=entry_id)

        assert self.balances[self.a] == Decimal(0)
