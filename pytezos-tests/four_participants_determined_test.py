""" Event: XTZ-USD dynamics would be > 1 in 12 hours after betting period of 24 hours.
    Liquidity pool 4%

    Three participants: a, b and c making next interactions:
        (1) participant A adds initial liquidity at the beginning (0 hours from start): 100k with ratio 1:1
        (2) participant B bets For with 50k (1 hour from start)
            rate before bet 50:50
            rate at bet     50:100, if S: win amount +25k*L, if ~S: loose amount -50k
            rate after bet  25:100 == 1:4 (a:f)
        (3) participant A adds more liquidity (12 hours from start): 50k with ratio 4:1 (f:a)
            NOTE: A whould probably have Ev =/= 0 after this operation
        (4) participant D adds more liquidity (12 hours from start): 450k with ratio 4:1 (f:a)
            NOTE: A whould probably have Ev =/= 0 after this operation
        (5) participant D bets Against with 125k (14 hours from start)
            rate before bet 500:125
            rate at bet     500:250 (f:a), if ~S: win amount +250k*L, if S: loose amount 125k
            rate after bet  250:250
        (6) participant C adds more liquidity at the very end (24 hours from start): 100k with ratio 1:1 (f:a)
            NOTE: C whould probably have Ev =/= 0 after this operation
        (7) particiapnt A calls running_measurement 26 hours from the start
        (8) oracle returns that price at the measurement start is 6.0$ per xtz. Oracle measurement time is behind one hour
        (9) participant B cals close_call at 38 hours from the start
        (10) oracle returns that price at the close is 7.5$ per xtz. Oracle measurement time is behind one hour

    Closed dynamics is +25%, betsFor pool is wins
                                      (1)      (2)      (3)       (4)       (5)       (6)
    Total event pool:               100_000 + 25_000 + 50_000 + 450_000 + 125_000 + 100_000 = 850_000
    betForLiquidityPool:             50_000 + 50_000 + 40_000 + 360_000 - 250_000 +  50_000 = 300_000
    betAgainstLiquidityPool:         50_000 - 25_000 + 10_000 +  90_000 + 125_000 +  50_000 = 300_000
            (liquidity rate is not included in the pools)

    if S:
        participant B wins and get 50_000 + 25_000 * 96% = 74_000 (this value should be saved in winning amounts ledger)
        participant D loose his bet 35_000 + provided liquidity 75_000
    if ~S:
        participant B loose his bet 50_000
        participant D wins and get 35_000 + 70_000 * 96% + provided liquidity 75_000 = 177_200

    Total win S  LP profit / loss:        0 - 24_000 +      0 +       0 + 125_000 +       0 = 101_000
    Total win ~S LP profit / loss:        0 + 50_000 +      0 +       0 - 120_000 +       0 = -70_000
            (liquidity rate is included in profit/loss pools)

    Total liquidity For bonuses:     50_000 +      0 + 20_000 + 180_000 +       0 +       0 = 250_000
    Total liquidity Against bonuses: 50_000 +      0 +  5_000 +  45_000 +       0 +       0 = 100_000
    Total provided Liquidity:       100_000 +      0 + 50_000 + 450_000 +       0 + 100_000 = 325_000

    Selected liquidity pool to distribute profits: liquidity Against (because For wins)

    liquidity For shares:
        A: 55_000 / 100_000 = 55%
        D: 45_000 / 100_000 = 45%
        C:      0 / 100_000 = 0%

    LP withdraw = Profit/Loss * LP_share + ProvidedL
    A withdraws: 101_000 * 0.55 + 100_000 + 50_000 = 205_550
    B withdraws: 50_000 + 24_000 = 74_000
    C withdraws: 100_000
    D withdraws: 101_000 * 0.45 + 450_000 = 495_450

    Changes:
        A: 205_550 / 150_000 = 1.370
        B:  74_000 /  50_000 = 1.480
        C: 100_000 / 100_000 = 1.000
        D: 495_450 / 575_000 = 0.862
"""

from state_transformation_base import StateTransformationBaseTest, RUN_TIME, ONE_HOUR
from pytezos import MichelsonRuntimeError


class FourParticipantsDeterminedTest(StateTransformationBaseTest):

    def test_with_four_participants(self):

        self.current_time = RUN_TIME
        self.id = len(self.storage['events'])

        # Creating event:
        amount = self.measure_start_fee + self.expiration_fee
        self.storage = self.check_new_event_succeed(
            event_params=self.default_event_params,
            amount=amount)

        # Participant A: adding liquidity 50/50 just at start:
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.a,
            amount=100_000,
            expected_for=1,
            expected_against=1)

        # Participant B: bets for 50_000 after 1 hour:
        self.current_time = RUN_TIME + ONE_HOUR
        self.storage = self.check_bet_succeed(
            participant=self.b,
            amount=50_000,
            bet='for',
            minimal_win=50_000)

        # Participant A: adding more liquidity after 12 hours (1/2 of the bets period):
        self.current_time = RUN_TIME + 12*ONE_HOUR
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.a,
            amount=50_000,
            expected_for=2,
            expected_against=1)

        # Participant D: adding more liquidity after 12 hours:
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.d,
            amount=450_000,
            expected_for=4,
            expected_against=1)

        # Participant D: bets against 125_000 after 12 hours:
        self.storage = self.check_bet_succeed(
            participant=self.d,
            amount=125_000,
            bet='against',
            minimal_win=125_000)

        # Participant C: adding more liquidity at the very end:
        self.current_time = RUN_TIME + 24*ONE_HOUR
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.c,
            amount=100_000,
            expected_for=1,
            expected_against=1)

        # Running measurement:
        self.current_time = RUN_TIME + 26*ONE_HOUR
        self.storage = self.check_start_measurement_succeed(sender=self.a)

        # Emulating callback:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time - 1*ONE_HOUR,
            'rate': 6_000_000
        }
        self.storage = self.check_start_measurement_callback_succeed(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address)
            
        # Closing event:
        self.current_time = RUN_TIME + 38*ONE_HOUR
        self.storage = self.check_close_succeed(sender=self.b)

        # Emulating calback with price is increased 25%:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time - 1*ONE_HOUR,
            'rate': 7_500_000
        }
        self.storage = self.check_close_callback_succeed(
            callback_values=callback_values,
            source=self.b,
            sender=self.oracle_address)

        # Withdrawals:
        self.current_time = RUN_TIME + 64*ONE_HOUR
        self.storage = self.check_withdraw_succeed(self.a, 205_550)
        self.storage = self.check_withdraw_succeed(self.b, 74_000)
        self.storage = self.check_withdraw_succeed(self.c, 100_000)
        self.storage = self.check_withdraw_succeed(self.d, 495_450)

