""" Test that checks that liquidity fee for bets calculation is correct """

from random import randint

from pytezos import MichelsonRuntimeError

from tests.interpret.juster.juster_base import ONE_HOUR
from tests.interpret.juster.juster_base import RUN_TIME
from tests.interpret.juster.juster_base import JusterBaseTestCase


class LiquidityFeeDynamicTest(JusterBaseTestCase):
    """This is experimental version of test with dynamic parameters.
    Trying to understand is it good or evil"""

    def test_liquidity_fee(self):

        self.current_time = RUN_TIME
        self.id = self.storage['nextEventId']

        # Liquidity percent is set to 1%:
        percent = int(self.storage['liquidityPrecision'] * 0.01)
        self.default_event_params['liquidityPercent'] = percent
        bets_close_time = self.default_event_params['betsCloseTime']
        bets_duration = bets_close_time - self.current_time

        # Creating event:
        self.new_event(
            event_params=self.default_event_params,
            amount=self.measure_start_fee + self.expiration_fee,
        )

        # Participant A: adding liquidity 1tez in both pools:
        self.provide_liquidity(
            participant=self.a,
            amount=1_000_000,
            expected_above_eq=1,
            expected_below=1,
        )

        # Participant B: bets for 1tez at different times and
        # have different possible win amount (adjusted by liq percent):

        def calculate_possible_win(current_time):
            possible_win = 500_000
            bet = 1_000_000
            elapsed_time = current_time - RUN_TIME
            multiplier = elapsed_time / bets_duration
            return int(bet + possible_win * (1 - 0.01 * multiplier))

        saved_storage = self.storage

        for test in range(10):
            # Model in tests and in contract works a little different with
            # divisions and sometimes it diverges by 1mutez. To simplify
            # this case, random_elapsed_time is in multiples of 1/100:
            # TODO: need to make model working the same way, man!

            self.storage = saved_storage.copy()
            random_elapsed_time = randint(0, 100) * bets_duration // 100
            self.current_time = RUN_TIME + random_elapsed_time
            self.bet(
                participant=self.b,
                amount=1_000_000,
                bet='aboveEq',
                minimal_win=1_000_000,
            )

            possible_win = self.storage['betsAboveEq'][(self.b, self.id)]
            calculated_win = calculate_possible_win(self.current_time)

            self.assertEqual(possible_win, calculated_win)
