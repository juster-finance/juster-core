from tests.test_data import generate_juster_config
from tests.interpret.pool.pool_base import PoolBaseTestCase
from random import randint


class NextEventLiquidityTestCase(PoolBaseTestCase):
    def test_that_next_event_liquidity_amount_calculated_properly(self):

        # creating default event:
        self.add_line(max_events=10)

        # providing liquidity:
        self.deposit_liquidity(self.a, amount=80_000_000)
        self.approve_liquidity(self.a, entry_id=0)
        self.assertEqual(self.get_next_liquidity(), 8_000_000)

        # second provider adds some liquidity with 20% shares:
        self.deposit_liquidity(self.b, amount=20_000_000)
        self.approve_liquidity(self.a, entry_id=1)
        self.assertEqual(self.get_next_liquidity(), 10_000_000)

        # creating one event:
        self.create_event(line_id=0, next_event_id=0)
        self.wait(3600)

        # A decided to remove liquidity:
        withdrawn_amount = self.claim_liquidity(
            self.a, position_id=0, shares=80_000_000)
        self.assertEqual(self.get_next_liquidity(), 2_000_000)

        # Run and finish event with profit 2xtz:
        self.create_event(line_id=0, next_event_id=1)
        self.wait(3600)
        self.pay_reward(event_id=1, amount=4_000_000)
        self.assertEqual(self.get_next_liquidity(), 2_200_000)

        # Run and finish event with loss 1xtz:
        self.create_event(line_id=0, next_event_id=2)
        self.wait(3600)
        self.pay_reward(event_id=2, amount=1_200_000)
        self.assertEqual(self.get_next_liquidity(), 2_100_000)


    def test_next_event_liquidity_cant_be_emptied_when_all_events_are_lose(self):

        # creating default event line:
        self.add_line(max_events=5)

        # providing liquidity:
        self.deposit_liquidity(self.a, amount=5_000_000)
        self.approve_liquidity(self.a, entry_id=0)

        for event_id in range(5):
            self.create_event(line_id=0, next_event_id=event_id)
            self.wait(3600)

        for event_id in range(5):
            self.pay_reward(event_id=event_id, amount=0)

        self.assertEqual(self.get_next_liquidity(), 0)


    def test_next_event_liquidity_shoul_be_equal_to_events_result_mean(self):

        def random_amount():
            return randint(1, 20) * 100_000

        # creating event line:
        self.add_line(max_events=5)

        # providing liquidity, value should not matter:
        self.deposit_liquidity(self.a, amount=random_amount()*5)
        self.approve_liquidity(self.a, entry_id=0)

        for event_id in range(5):
            self.create_event(line_id=0)
            self.wait(3600)

        mean_amount = 0
        for event_id in range(5):
            amount = random_amount()
            self.pay_reward(event_id=event_id, amount=amount)
            mean_amount += amount / 5

        self.assertEqual(self.get_next_liquidity(), mean_amount)


    def test_next_event_liquidity_with_two_lines_and_one_emptied(self):

        # creating default event line:
        self.add_line(max_events=5)
        self.add_line(max_events=5)

        # providing liquidity:
        self.deposit_liquidity(self.a, amount=10_000_000)
        self.approve_liquidity(self.a, entry_id=0)
        self.assertEqual(self.get_next_liquidity(), 1_000_000)

        # creating events for only one line:
        second_line_event_ids = []
        for event_id in range(5):
            self.create_event(line_id=0)
            self.wait(3600)

        for event_id in range(5):
            self.pay_reward(event_id=event_id, amount=0)

        # there are should be liquidity for the second line:
        self.assertEqual(self.get_next_liquidity(), 500_000)


    def test_next_event_liquidity_cant_be_emptied_when_provider_goes_out(self):

        # creating default event line:
        self.add_line(max_events=2)

        # providing liquidity:
        self.deposit_liquidity(self.a, amount=2_000_000)
        self.approve_liquidity(self.a, entry_id=0)

        self.create_event()
        self.wait(3600)
        self.claim_liquidity(self.a, shares=2_000_000)

        self.pay_reward(event_id=0, amount=0)

        self.assertEqual(self.get_next_liquidity(), 0)


    def test_event_creation_fees_included_in_costs(self):

        custom_config = generate_juster_config(
            measure_start_fee=200_000,
            expiration_fee=100_000)

        self.add_line(max_events=2)

        # providing liquidity:
        self.deposit_liquidity(self.a, amount=1_000_000)
        self.approve_liquidity(self.a, entry_id=0)

        self.create_event(config=custom_config)
        self.assertEqual(self.get_next_liquidity(), 500_000)
        self.assertEqual(self.storage['events'][0]['provided'], 500_000)
        self.wait(3600)

        self.pay_reward(event_id=0, amount=200_000)
        self.assertEqual(self.get_next_liquidity(), 350_000)

        self.create_event(config=custom_config)
        self.assertEqual(self.storage['events'][1]['provided'], 350_000)
        self.wait(3600)


    def test_next_event_liquidity_should_not_be_changed_by_locked_liquidity(self):
        # This is case catched in hanzhounet, error was in payReward with
        # locked profits/losses that should not be distributed

        # creating default event line:
        self.add_line(max_events=2)

        # providing liquidity:
        self.deposit_liquidity(self.a, amount=2_000_000)
        self.approve_liquidity(self.a, entry_id=0)

        self.create_event()
        self.claim_liquidity(self.a, shares=2_000_000)
        self.assertEqual(self.get_next_liquidity(), 0)

        self.wait(3600)
        self.pay_reward(event_id=0, amount=4_000_000)

        self.withdraw_liquidity(positions=[{'eventId': 0, 'positionId': 0}])

        self.assertEqual(self.get_next_liquidity(), 0)

    def test_should_not_change_next_event_liquidity_after_update(self):
        # this case tests liquidity precision

        # creating 9x2 event lines:
        for _ in range(9):
            self.add_line(max_events=2)

        self.deposit_liquidity(self.a, amount=18_000_000)
        self.approve_liquidity(self.a, entry_id=0)

        self.assertEqual(self.get_next_liquidity(), 1_000_000)

        # updating lines:
        for _ in range(9):
            self.add_line(max_events=2)
        for line_id in range(9):
            self.trigger_pause_line(line_id=line_id)

        # anyway int round 9.9999 to 9, so there will be little differences:
        difference = self.get_next_liquidity() - 1_000_000
        self.assertTrue(difference <= 1)


    def test_next_event_liquidity_with_event_creation_fee(self):
        # this case represents case from testnet launch
        self.add_line(max_events=2, bets_period=100, measure_period=100)

        self.deposit_liquidity(self.a, amount=2_000_000)
        self.approve_liquidity(self.a, entry_id=0)

        event_0 = self.create_event()
        self.wait(100)
        event_1 = self.create_event()
        self.wait(100)

        self.pay_reward(event_id=event_0, amount=900_000)
        event_3 = self.create_event()

