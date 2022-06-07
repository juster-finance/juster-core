from random import randint

from tests.interpret.pool.pool_base import PoolBaseTestCase


class PrecisionPoolTestCase(PoolBaseTestCase):
    def test_should_calc_withdrawable_f_with_enough_precision(self):
        self.add_line(max_events=1)
        provider_address = self.a
        entry_id = self.deposit_liquidity(amount=60, sender=provider_address)
        position_id = self.approve_liquidity(entry_id=entry_id)
        event_id = self.create_event()
        self.claim_liquidity(position_id=position_id, shares=20)
        self.pay_reward(event_id=event_id, amount=60)

        self.assertEqual(
            self.storage['withdrawableLiquidityF'],
            20 * self.storage['precision']
        )

        payouts = self.withdraw_liquidity(
            [{'positionId': position_id, 'eventId': event_id}]
        )
        self.assertEqual(payouts[provider_address], 20)

    def test_should_not_accumulate_precision_error_in_active_liquidity(self):
        self.add_line(max_events=1)
        entry_id = self.deposit_liquidity(amount=17)
        position_id = self.approve_liquidity(entry_id=entry_id)
        event_id = self.create_event()
        self.claim_liquidity(position_id=position_id, shares=11)
        self.assertEqual(
            self.storage['activeLiquidityF'],
            6 * self.storage['precision']
        )
        self.pay_reward(event_id=event_id, amount=17)
