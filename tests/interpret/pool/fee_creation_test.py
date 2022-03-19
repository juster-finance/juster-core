from tests.interpret.pool.pool_base import PoolBaseTestCase
from pytezos import MichelsonRuntimeError


class FeeEventCreationTestCase(PoolBaseTestCase):
    def test_next_event_liquidity_should_include_future_fees(self):

        self.storage['newEventFee'] = 500_000

        # creating default event:
        self.add_line(max_active_events=3)

        # providing liquidity:
        self.deposit_liquidity(self.a, amount=4_500_000)
        self.approve_liquidity(self.a, entry_id=0)
        self.assertEqual(self.get_next_liquidity(), 1_500_000)

        # second provider adds the same amount of liquidity:
        self.deposit_liquidity(self.b, amount=4_500_000)
        self.approve_liquidity(self.a, entry_id=1)

        # and all of this liquidity should go to the events:
        self.assertEqual(self.get_next_liquidity(), 3_000_000)

        # creating one event:
        self.create_event(event_line_id=0, next_event_id=0)
        self.wait(3600)

        # A decided to remove all liquidity so nextEventLiquidity should be /2:
        withdrawn_amount = self.claim_liquidity(
            self.a, position_id=0, shares=4_500_000)
        self.assertEqual(withdrawn_amount, 3_000_000)
        self.assertEqual(self.get_next_liquidity(), 1_500_000)

        # Run and finish event with profit 3xtz (provided 1xtz, 0.5xtz fee):
        self.create_event(event_line_id=0, next_event_id=1)
        self.wait(3600)
        self.pay_reward(event_id=1, amount=4_500_000)
        self.assertEqual(self.get_next_liquidity(), 2_500_000)

        # Finishing first event with no profit (first event was created
        # in 17th line with 2.5xtz + 0.5xtz fee):
        self.pay_reward(event_id=0, amount=3_000_000)
        self.assertEqual(self.get_next_liquidity(), 2_500_000)

        # Creating another line that should increase next event creation reserves:
        # 2.5 * 3 / (3+2) = 1.5
        self.add_line(max_active_events=2)
        self.assertEqual(self.get_next_liquidity(), 1_500_000)


    def test_should_fail_to_create_event_if_fee_more_than_next_event_liquidity(self):

        self.storage['newEventFee'] = 500_000

        # creating default event:
        self.add_line(max_active_events=3)

        # providing liquidity that only covers new event fees:
        self.deposit_liquidity(self.a, amount=1_500_000)
        self.approve_liquidity(self.a, entry_id=0)
        self.assertEqual(self.get_next_liquidity(), 500_000)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.create_event(event_line_id=0, next_event_id=1)
        msg = 'Not enough liquidity to run event'
        self.assertTrue(msg in str(cm.exception))

