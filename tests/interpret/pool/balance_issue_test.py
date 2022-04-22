from tests.interpret.pool.pool_base import PoolBaseTestCase
from pytezos import MichelsonRuntimeError


class BalanceIssueTestCase(PoolBaseTestCase):

    def test_should_allow_participants_claim_if_their_claims_rounded_againts_pool(self):
        self.add_line(max_events=3)
        entry_id = self.deposit_liquidity(amount=1_000_000)
        position_one = self.approve_liquidity(entry_id=entry_id)

        entry_id = self.deposit_liquidity(amount=1_000_001)
        position_two = self.approve_liquidity(entry_id=entry_id)

        first_event = self.create_event()
        self.wait(3600)
        second_event = self.create_event()
        self.wait(3600)

        self.claim_liquidity(shares=1_000_000, position_id=position_one)
        self.claim_liquidity(shares=1_000_001, position_id=position_two)
        assert self.balances['contract'] >= 0

        self.pay_reward(event_id=first_event, amount=1_000_000)
        self.pay_reward(event_id=second_event, amount=1_000_000)

        self.withdraw_liquidity(positions=[
            {'positionId': position_one, 'eventId': first_event},
            {'positionId': position_one, 'eventId': second_event},
            {'positionId': position_two, 'eventId': first_event},
            {'positionId': position_two, 'eventId': second_event}
        ])

        # checing continuality:
        entry_id = self.deposit_liquidity(amount=1_000_000)
        new_position = self.approve_liquidity(entry_id=entry_id)
        self.assertEqual(
            self.storage['positions'][new_position]['shares'],
            1_000_000
        )

        self.claim_liquidity(shares=1_000_000, position_id=new_position)
        # NOTE: contract kept positive balance and positive withdrawableLiquidity sum
        # positive balance is OK, but withdrawableLiquidity > 0 may bring some promlems

