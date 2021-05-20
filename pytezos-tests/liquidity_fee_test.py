""" Test that checks that liquidity fee for bets calculation is correct """

from state_transformation_base import StateTransformationBaseTest, RUN_TIME, ONE_HOUR
from pytezos import MichelsonRuntimeError
from random import randint


class LiquidityFeeDynamicTest(StateTransformationBaseTest):
    """ This is experimental version of test with dynamic parameters.
        Trying to understand is it good or evil """

    def test_liquidity_fee(self):

        self.current_time = RUN_TIME
        self.id = len(self.storage['events'])

        # Liquidity percent is set to 1%:
        percent = int(self.storage['liquidityPrecision'] * 0.01)
        self.default_config['liquidityPercent'] = percent
        bets_close_time = self.default_event_params['betsCloseTime']
        bets_duration = bets_close_time - self.current_time

        # Creating event:
        self.storage = self.check_new_event_succeed(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee)

        # Participant A: adding liquidity 1tez in both pools:
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.a,
            amount=2_000_000,
            expected_for=1,
            expected_against=1)

        # Participant B: bets for 1tez at different times and
        # have different possible win amount (adjusted by liq percent):

        def calculate_possible_win(current_time):
            possible_win = 500_000
            bet = 1_000_000
            elapsed_time = current_time - RUN_TIME
            multiplier = elapsed_time / bets_duration
            return int(bet + possible_win * (1 - 0.01*multiplier))

        """
        possible_wins_at_time = {
            # at the event start time liquidity percent is 0%:
            RUN_TIME:                          1_000_000 + 500_000,

            # after 50% of time liquidity percent is 0.5%:
            RUN_TIME + bets_duration // 2:     1_000_000 + 497_500,

            # after 75% of time liquidity percent is 0.75%:
            RUN_TIME + bets_duration * 3 // 4: 1_000_000 + 496_250,

            # after 100% of time liquidity percent is 1%:
            RUN_TIME + bets_duration: 1_000_000 + 495_000
        }

        for current_time, win_amount in possible_wins_at_time.items():
            self.current_time = current_time
            result_storage = self.check_bet_succeed(
                participant=self.b,
                amount=1_000_000,
                bet='for',
                minimal_win=1_000_000)

            possible_win = result_storage['betsFor'][(self.b, self.id)]
            self.assertEqual(possible_win, win_amount)
        """

        for test in range(10):
            # Model in tests and in contract works a little different with
            # divisions and sometimes it diverges by 1mutez. To simplify
            # this case, random_elapsed_time is in multiples of 1/100:

            random_elapsed_time = randint(0, 100) * bets_duration // 100
            self.current_time = RUN_TIME + random_elapsed_time
            result_storage = self.check_bet_succeed(
                participant=self.b,
                amount=1_000_000,
                bet='for',
                minimal_win=1_000_000)

            possible_win = result_storage['betsFor'][(self.b, self.id)]
            calculated_win = calculate_possible_win(self.current_time)

            self.assertEqual(possible_win, calculated_win)

