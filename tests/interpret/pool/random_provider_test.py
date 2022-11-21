from random import randint
from random import seed

from tests.interpret.pool.pool_base import PoolBaseTestCase


class RandomProviderTestCase(PoolBaseTestCase):
    def test_provider_should_get_calculated_reward_in_multiple_events(self):
        SEED = randint(0, 10**16)
        seed(SEED)
        ITERATIONS = 5

        for _ in range(ITERATIONS):
            self.drop_changes()
            STEPS = 10
            ENTER_STEP = randint(0, STEPS - 1)
            EXIT_STEP = randint(ENTER_STEP, STEPS - 1)
            PROFIT_LOSS = randint(-10, 10) * 300_000

            self.add_line(max_events=3)

            # A is core provider:
            shares = 90_000_000
            total_liquidity = 90_000_000
            self.deposit_liquidity(self.a, amount=total_liquidity)
            self.approve_entry(self.a, entry_id=0)

            for step in range(STEPS):

                if step == ENTER_STEP:
                    self.deposit_liquidity(self.b, amount=total_liquidity)
                    self.approve_entry(self.b, entry_id=1)

                created_id = self.create_event()
                self.wait(3600)
                self.pay_reward(
                    event_id=created_id,
                    amount=self.get_next_liquidity() + PROFIT_LOSS,
                )
                total_liquidity += PROFIT_LOSS

                if step == EXIT_STEP:
                    self.claim_liquidity(
                        self.b, provider=self.b, shares=shares
                    )

            provider_profit_loss = (
                (EXIT_STEP - ENTER_STEP + 1) * PROFIT_LOSS / 2
            )
            self.assertEqual(self.balances[self.b], provider_profit_loss)

    def test_all_providers_should_have_zero_balance_at_the_end(self):
        SEED = randint(0, 10**16)
        seed(SEED)

        STEPS = 20
        AMOUNT = 100
        EVENTS_COUNT = 5
        EVENT_DURATION = 3600
        STEP_DURATION = 600

        enter_steps = {
            self.a: 0,
            self.b: randint(0, STEPS - 1),
            self.c: randint(0, STEPS - 1),
            self.d: randint(0, STEPS - 1),
        }

        exit_steps = {
            self.a: STEPS - 1,
            self.b: randint(enter_steps[self.b], STEPS - 1),
            self.c: randint(enter_steps[self.c], STEPS - 1),
            self.d: randint(enter_steps[self.d], STEPS - 1),
        }

        event_create_steps = {
            line_id: randint(0, STEPS - 7) for line_id in range(EVENTS_COUNT)
        }

        [self.add_line(max_events=1) for _ in event_create_steps]

        close_event_times = {}
        position_ids = {}

        for step in range(STEPS):
            for user, enter_step in enter_steps.items():
                if step == enter_step:
                    entry_id = self.deposit_liquidity(user, amount=AMOUNT)
                    pos_id = self.approve_entry(user, entry_id=entry_id)
                    position_ids[user] = pos_id

            for line_id, event_create_step in event_create_steps.items():
                if step == event_create_step:
                    created_id = self.create_event(line_id=line_id)
                    close_event_times[created_id] = (
                        self.current_time + EVENT_DURATION
                    )

            self.wait(STEP_DURATION)

            close_events = [
                event_id
                for event_id, close_time in close_event_times.items()
                if close_time <= self.current_time
            ]

            for event_id in close_events:
                provided_amount = self.storage['events'][event_id]['provided']
                self.pay_reward(event_id=event_id, amount=provided_amount)
                close_event_times.pop(event_id)

            for user, exit_step in exit_steps.items():
                if step == exit_step:
                    pos_id = position_ids[user]
                    shares = self.storage['shares'][user]
                    self.claim_liquidity(user, provider=user, shares=shares)

        claims = [
            dict(provider=claim[1], eventId=claim[0])
            for claim in self.storage['claims']
        ]

        self.withdraw_claims(claims=claims)

        is_all_balance_less_than_mutez = all(
            abs(balance) <= 1 for balance in self.balances.values()
        )

        self.assertTrue(is_all_balance_less_than_mutez)
