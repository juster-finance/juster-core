from pytezos import MichelsonRuntimeError

from tests.interpret.pool.pool_base import PoolBaseTestCase


class BigNumbersTestCase(PoolBaseTestCase):
    def test_should_allow_to_provide_trillions(self):
        big_amount = 10**18
        self.add_line(max_events=2)
        self.deposit_liquidity(amount=big_amount)
        provider = self.approve_entry()
        first_event = self.create_event()
        self.wait(3600)
        self.claim_liquidity(shares=int(big_amount * 0.2))
        second_event = self.create_event()
        self.pay_reward(event_id=first_event, amount=int(big_amount * 0.5))
        self.wait(3600)
        self.claim_liquidity(shares=int(big_amount * 0.8))
        self.pay_reward(
            event_id=second_event, amount=int(big_amount * 0.5 * 0.8)
        )
        self.withdraw_claims(
            claims=[
                {'provider': provider, 'eventId': first_event},
                {'provider': provider, 'eventId': second_event},
            ]
        )
