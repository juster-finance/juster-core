""" Event: XTZ-USD dynamics would be > 1 in 12 hours after betting period of 24 hours.
    Liquidity pool 0%

    Four participants: a, b, c and d making next interactions:
        (1) participant A adds initial liquidity at the beginning (0 hours from start): 50k with ratio 1:1
        (2) participant B bets AboveEq with 50k (1 hour from start)
            rate before bet 50:50
            rate at bet     50:100, if S: win amount +25k*L, if ~S: loose amount -50k
            rate after bet  25:100 == 1:4 (a:f)

        (3) participant A adds more liquidity (12 hours from start): 40k with ratio 4:1 (f:a)
            totalLiquidityShares: 100
            newShares for A: 40

        (4) participant D adds more liquidity (12 hours from start): 360k with ratio 4:1 (f:a)
            totalLiquidityShares: 140
            newShares for D: 360

        (5) participant D bets Below with 125k (14 hours from start)
            rate before bet 500:125
            rate at bet     500:250 (f:a), if ~S: win amount +250k*L, if S: loose amount 125k
            rate after bet  250:250

        (6) participant C adds more liquidity at the very end (24 hours from start): 50k with ratio 1:1 (f:a)
            totalLiquidityShares: 500
            newShares for C: 50/250 * 500 = 100

        (7) particiapnt A calls running_measurement 26 hours from the start
        (8) oracle returns that price at the measurement start is 6.0$ per xtz. Oracle measurement time is behind one hour
        (9) participant B cals close_call at 38 hours from the start
        (10) oracle returns that price at the close is 7.5$ per xtz. Oracle measurement time is behind one hour

    Closed dynamics is +25%, betsAboveEq pool is wins
                                      (1)      (2)      (3)       (4)       (5)       (6)
    Total event pool:               50_000 + 25_000 + 40_000 + 360_000 + 125_000 +  50_000 = 850_000
    A:                              50_000 + 50_000 + 40_000 + 360_000 - 250_000 +  50_000 = 300_000
    B:                              50_000 - 25_000 + 10_000 +  90_000 + 125_000 +  50_000 = 300_000
            (liquidity rate is not included in the pools)

    Selected liquidity pool to distribute profits: liquidity Below (because AboveEq wins)

    liquidity AboveEq profit / loss distribution:
        A: -25_000 * 1.00 + 125_000 * 140/500 = 10_000
        D: 360/500 * 125_000 = 90_000
        C: 0

    LP withdraw = Profit/Loss * LP_share + ProvidedL
    A withdraws: 10_000 + 50_000 + 40_000 = 100_000
    B withdraws: 50_000 + 25_000 = 75_000
    C withdraws: 50_000
    D withdraws: 90_000 + 360_000 = 450_000

    Changes:
        A: 100_000 /  90_000 = 1.111
        B:  75_000 /  50_000 = 1.500
        C: 50_000  /  50_000 = 1.000
        D: 450_000 / 485_000 = 0.927
"""

from juster_base import JusterBaseTestCase, RUN_TIME, ONE_HOUR
from pytezos import MichelsonRuntimeError


class FourParticipantsDeterminedTest(JusterBaseTestCase):

    def test_with_four_participants(self):

        self.current_time = RUN_TIME
        self.id = self.storage['nextEventId']

        # Creating event:
        amount = self.measure_start_fee + self.expiration_fee
        self.storage = self.check_new_event_succeed(
            event_params=self.default_event_params,
            amount=amount)

        # Participant A: adding liquidity 50/50 just at start:
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.a,
            amount=50_000,
            expected_above_eq=1,
            expected_below=1)

        # Participant B: bets aboveEq 50_000 after 1 hour:
        self.current_time = RUN_TIME + ONE_HOUR
        self.storage = self.check_bet_succeed(
            participant=self.b,
            amount=50_000,
            bet='aboveEq',
            minimal_win=50_000)

        # Participant A: adding more liquidity after 12 hours (1/2 of the bets period):
        self.current_time = RUN_TIME + 12*ONE_HOUR
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.a,
            amount=40_000,
            expected_above_eq=4,
            expected_below=1)

        # Participant D: adding more liquidity after 12 hours:
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.d,
            amount=360_000,
            expected_above_eq=4,
            expected_below=1)

        # Participant D: bets below 125_000 after 12 hours:
        self.storage = self.check_bet_succeed(
            participant=self.d,
            amount=125_000,
            bet='below',
            minimal_win=125_000)

        # Participant C: adding more liquidity at the very end:
        self.current_time = RUN_TIME + 24*ONE_HOUR
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.c,
            amount=50_000,
            expected_above_eq=1,
            expected_below=1)

        # Running measurement:
        self.current_time = RUN_TIME + 26*ONE_HOUR

        # Emulating callback:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time - 1*ONE_HOUR,
            'rate': 6_000_000
        }
        self.storage = self.check_start_measurement_succeed(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address)

        # Closing event:
        self.current_time = RUN_TIME + 38*ONE_HOUR

        # Emulating calback with price is increased 25%:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time - 1*ONE_HOUR,
            'rate': 7_500_000
        }
        self.storage = self.check_close_succeed(
            callback_values=callback_values,
            source=self.b,
            sender=self.oracle_address)

        # Withdrawals:
        self.current_time = RUN_TIME + 64*ONE_HOUR
        self.storage = self.check_withdraw_succeed(self.b,  75_000)
        self.storage = self.check_withdraw_succeed(self.a, 100_000)
        self.storage = self.check_withdraw_succeed(self.c,  50_000)
        self.storage = self.check_withdraw_succeed(self.d, 450_000)
