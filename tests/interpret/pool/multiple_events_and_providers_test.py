from tests.interpret.pool.pool_base import PoolBaseTestCase


class MultipleEventsAndProvidersTest(PoolBaseTestCase):
    def test_multiple_events_and_providers(self):

        # creating multiple lines with different pairs:
        self.add_line(currency_pair='XTZ-USD', max_events=1)
        self.add_line(currency_pair='ETH-USD', max_events=1)
        self.add_line(currency_pair='BTC-USD', max_events=1)

        # providing liquidity with first provider:
        self.deposit_liquidity(self.a, amount=3_000_000)
        self.approve_liquidity(self.a, entry_id=0)
        self.assertEqual(self.get_next_liquidity(), 1_000_000)

        # running two events, in each should be added 1xtz:
        self.create_event(line_id=0, next_event_id=0)
        self.create_event(line_id=1, next_event_id=1)

        # second provider adds the same amount of liquidity:
        self.deposit_liquidity(self.b, amount=3_000_000)
        self.approve_liquidity(self.a, entry_id=1)
        self.assertEqual(self.get_next_liquidity(), 2_000_000)

        # running last event with 2xtz liquidity:
        self.create_event(line_id=2, next_event_id=2)

        self.wait(3600)

        # let first two events be profitable (+0.9 xtz):
        self.pay_reward(event_id=0, amount=1_900_000)
        self.assertEqual(self.get_next_liquidity(), 2_300_000)

        self.pay_reward(event_id=1, amount=1_900_000)
        self.assertEqual(self.get_next_liquidity(), 2_600_000)

        # and last one is not (-1.8 xtz):
        self.pay_reward(event_id=2, amount=200_000)
        self.assertEqual(self.get_next_liquidity(), 2_000_000)

        # The second cycle both providers in place:
        self.create_event(line_id=0, next_event_id=3)
        self.create_event(line_id=1, next_event_id=4)
        self.create_event(line_id=2, next_event_id=5)

        self.wait(3600)
        self.pay_reward(event_id=3, amount=3_000_000)
        self.pay_reward(event_id=4, amount=1_000_000)
        self.pay_reward(event_id=5, amount=4_000_000)

        # Both providers should have the same shares and should earn 2xtz:
        # removing liquidity:
        withdrawn_amount = self.claim_liquidity(
            self.a, position_id=0, shares=3_000_000)
        self.assertEqual(withdrawn_amount, 4_000_000)

        withdrawn_amount = self.claim_liquidity(
            self.b, position_id=1, shares=3_000_000)
        self.assertEqual(withdrawn_amount, 4_000_000)

