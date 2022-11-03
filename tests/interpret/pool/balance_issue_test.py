from pytezos import MichelsonRuntimeError
from decimal import Decimal

from tests.interpret.pool.pool_base import PoolBaseTestCase


class BalanceIssueTestCase(PoolBaseTestCase):
    def test_should_allow_participants_claim_if_their_claims_rounded_againts_pool(
        self,
    ):
        self.add_line(max_events=3)
        entry_id = self.deposit_liquidity(amount=1_000_000, sender=self.a)
        provider_one = self.approve_liquidity(entry_id=entry_id)

        entry_id = self.deposit_liquidity(amount=1_000_001, sender=self.b)
        provider_two = self.approve_liquidity(entry_id=entry_id)

        first_event = self.create_event()
        self.wait(3600)
        second_event = self.create_event()
        self.wait(3600)

        self.claim_liquidity(
            shares=1_000_000,
            provider=provider_one,
            sender=provider_one,
        )
        self.claim_liquidity(
            shares=1_000_001,
            provider=provider_two,
            sender=provider_two,
        )
        assert self.balances['contract'] >= 0

        self.pay_reward(event_id=first_event, amount=1_000_000)
        self.pay_reward(event_id=second_event, amount=1_000_000)

        claims = [
            {'provider': provider_one, 'eventId': first_event},
            {'provider': provider_one, 'eventId': second_event},
            {'provider': provider_two, 'eventId': first_event},
            {'provider': provider_two, 'eventId': second_event},
        ]
        self.withdraw_liquidity(claims=claims)

        # checing continuality:
        entry_id = self.deposit_liquidity(amount=1_000_000)
        new_provider = self.approve_liquidity(entry_id=entry_id)
        self.assertEqual(
            self.storage['shares'][new_provider], 1_000_000
        )

        self.claim_liquidity(shares=1_000_000, provider=new_provider)
        # allowing 1 mutez on the contract:
        self.assertTrue(self.balances['contract'] <= Decimal(1))

    def test_participant_should_be_able_to_claim_liquidity_when_it_all_active(
        self,
    ):
        self.add_line(max_events=3)
        entry_id = self.deposit_liquidity(amount=1_000_000)
        provider = self.approve_liquidity(entry_id=entry_id)

        first_event = self.create_event()
        self.wait(3600)
        second_event = self.create_event()
        self.wait(3600)
        third_event = self.create_event()

        self.claim_liquidity(shares=1_000, provider=provider)
        self.claim_liquidity(shares=1, provider=provider)

    def test_negative_payout_issue_when_provided_approved_during_loss_event(
        self,
    ):

        self.add_line(max_events=2)
        entry_id = self.deposit_liquidity(amount=1000)
        provider = self.approve_liquidity(entry_id=entry_id)

        first_event = self.create_event()
        self.wait(3600)
        second_event = self.create_event()
        self.wait(3600)

        entry_id = self.deposit_liquidity(amount=1000)
        self.approve_liquidity(entry_id=entry_id)

        # event finished with loss 400, free liquidity is 1000 + 100 = 1100
        self.pay_reward(event_id=first_event, amount=100)

        # total liquidity is 100 + 1000 + 500 = 1600, event created with 50%:
        self.create_event()

        # free liquidity = 1100 - 800 = 300
        payout = self.claim_liquidity(shares=1_000, provider=provider)

        # payout is 50% of free liquidity = 50% * 300:
        self.assertEqual(payout, 150)

    def test_negative_payout_issue_when_provided_approved_during_loss_event_b(
        self,
    ):
        """Similar to previous test that represents wrong claim liquidity
        payout for second position"""

        self.add_line(max_events=2)
        entry_id = self.deposit_liquidity(amount=1000)
        provider_one = self.approve_liquidity(entry_id=entry_id)

        first_event = self.create_event()
        self.wait(3600)
        second_event = self.create_event()
        self.wait(3600)

        entry_id = self.deposit_liquidity(amount=1000)
        provider_two = self.approve_liquidity(entry_id=entry_id)

        self.pay_reward(event_id=first_event, amount=100)
        third_event = self.create_event()

        # there is only 300 mutez on balance but pool tries to pay 400 with
        # current calculations:
        payout = self.claim_liquidity(shares=1_000, provider=provider_two)
        self.assertEqual(payout, 150)

    def test_payout_should_not_exceed_balance_when_there_was_lmt_shares_event(
        self,
    ):

        self.add_line(max_events=2)
        entry_id = self.deposit_liquidity(amount=1000)
        provider = self.approve_liquidity(entry_id=entry_id)

        first_event = self.create_event()
        self.wait(3600)
        second_event = self.create_event()
        self.wait(3600)
        self.pay_reward(event_id=first_event, amount=100)
        third_event = self.create_event()
        self.assertEqual(self.balances['contract'], 0)

        payout = self.claim_liquidity(shares=100, provider=provider)
        self.assertEqual(payout, 0)
