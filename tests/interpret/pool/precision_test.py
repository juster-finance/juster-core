from random import randint

from tests.interpret.pool.pool_base import PoolBaseTestCase


class PrecisionPoolTestCase(PoolBaseTestCase):
    def test_should_calc_withdrawable_f_with_enough_precision(self):
        self.add_line(max_events=1)
        entry_id = self.deposit_liquidity(amount=60, sender=self.a)
        provider = self.approve_entry(entry_id=entry_id)
        event_id = self.create_event()
        self.claim_liquidity(provider=provider, shares=20)
        self.pay_reward(event_id=event_id, amount=60)

        self.assertEqual(
            self.storage['withdrawableLiquidityF'],
            20 * self.storage['precision'],
        )

        payouts = self.withdraw_claims(
            [{'provider': provider, 'eventId': event_id}]
        )
        self.assertEqual(payouts[provider], 20)

    def test_should_not_accumulate_precision_error_in_active_liquidity(self):
        self.add_line(max_events=1)
        entry_id = self.deposit_liquidity(amount=17)
        provider = self.approve_entry(entry_id=entry_id)
        event_id = self.create_event()
        self.claim_liquidity(provider=provider, shares=11)
        self.assertEqual(
            self.storage['activeLiquidityF'], 6 * self.storage['precision']
        )
        self.pay_reward(event_id=event_id, amount=17)

    def test_should_not_accumulate_precision_error_in_active_liquidity_B(self):
        self.add_line(max_events=1)
        entry_id = self.deposit_liquidity(amount=40)
        provider_one = self.approve_entry(entry_id=entry_id)
        event_id = self.create_event()

        entry_id = self.deposit_liquidity(amount=20)
        provider_two = self.approve_entry(entry_id=entry_id)
        payout = self.claim_liquidity(provider=provider_two, shares=20)

        self.pay_reward(event_id=event_id, amount=40)
        self.assertEqual(self.storage['activeLiquidityF'], 0)

    def test_should_distribute_claims_fairly_when_rounds_up(self):
        # this is simplified case from the random test:
        # test_all_providers_should_have_zero_balance_at_the_end
        # with the seed = 1757271336181368

        # NOTE: this effect does not scale so looks like this test is not so
        # important and might be removed

        SCALE = 1000
        provider_address = self.c

        self.add_line(max_events=5)
        entry_id = self.deposit_liquidity(
            amount=200 * SCALE, sender=provider_address
        )
        provider_one = self.approve_entry(entry_id=entry_id)

        # starting two events, each should receive 40 mutez as provided:
        event_one_id = self.create_event()
        self.wait(3600)
        event_two_id = self.create_event()

        # second provider adds 100 shares and claims it instantly:
        entry_id = self.deposit_liquidity(
            amount=100 * SCALE, sender=provider_address
        )
        provider_two = self.approve_entry(entry_id=entry_id)
        instant_payout = self.claim_liquidity(
            provider=provider_two,
            shares=100 * SCALE,
            sender=provider_address,
        )

        # two events finishes without profit/loss:
        self.pay_reward(event_id=event_one_id, amount=40 * SCALE)
        self.pay_reward(event_id=event_two_id, amount=40 * SCALE)

        # 2nd provider withdraws claims and shouldn't get more than provided:
        payouts = self.withdraw_claims(
            claims=[
                {'eventId': event_one_id, 'provider': provider_two},
                {'eventId': event_two_id, 'provider': provider_two},
            ]
        )

        payout_sum = instant_payout + payouts[provider_address]
        diff = abs(payout_sum - 100 * SCALE)
        self.assertTrue(diff <= 1)
