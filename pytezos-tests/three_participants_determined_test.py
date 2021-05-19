""" Event: XTZ-USD dynamics would be > 1 in 12 hours after betting period of 24 hours.
    Liquidity pool 0%

    Three participants: a, b and c making next interactions:
        (1) participant A adds initial liquidity at the beginning (0 hours from start): 100k with ratio 1:1
        (2) participant B betFor with 50k (1 hour from start)
            rate at bet 50:100, if S: win amount +25k*L, if ~S: loose amount -50k
            rate after bet 100:25 == 4:1
        (3) participant A adds more liquidity (12 hours from start): 50k with ratio 4:1 (f:a)
        (4) participant C adds more liquidity at the very end (24 hours from start): 100k with ratio 4:1 (f:a)
        (5) particiapnt A calls running_measurement 26 hours from the start
        (6) oracle returns that price at the measurement start is 6.0$ per xtz. Oracle measurement time is behind one hour
        (7) participant B cals close_call at 38 hours from the start
        (8) oracle returns that price at the close is 7.5$ per xtz. Oracle measurement time is behind one hour

    Closed dynamics is +25%, betsFor pool is wins
                                    (1)      (2)      (3)       (4)
    Total event pool:               100_000 + 25_000 + 50_000 + 100_000 = 265_000
    betForLiquidityPool:             50_000 + 50_000 + 40_000 +  80_000 = 220_000
    betAgainstLiquidityPool:         50_000 - 25_000 + 10_000 +  20_000 =  55_000
            (liquidity rate is not included in the pools)

    if participant B wins he get 50_000 + 25_000 * 100% = 75_000 (this value should be saved in winning amounts ledger)

    Total win S  LP profit / loss:        0 - 25_000 +      0 +       0 = -25_000  (including L bonus for winnig returns)
    Total win ~S LP profit / loss:        0 + 50_000 +      0 +       0 =  50_000  (and not including L bonus for bets)
            (liquidity rate is included in profit/loss pools)

    Total liquidity For bonuses:     50_000 +      0 + 20_000 +       0 =  70_000
    Total liquidity Against bonuses: 50_000 +      0 +  5_000 +       0 =  55_000
    Total provided Liquidity:       100_000 +      0 + 50_000 + 100_000 = 250_000

    selected liquidity pool to distribute profits: liquidity Against

    liquidity Against shares:
        A: 55_000 / 55_000 = 100%
        C: 0      / 55_000 = 0%

    LP withdraw = Profit/Loss * LP_share + ProvidedL
    A withdraws: -24_000 * 100% + 100_000 + 50_000 = 126_000
    C withdraws: 100_000

    Changes:
        A: 125_000 / 150_000 = 0.840
        B: 75_000 / 50_000 = 1.480
        C: 100_000 / 100_000 = 1.000
"""

from state_transformation_base import (
    StateTransformationBaseTest, RUN_TIME, ONE_HOUR)
from pytezos import MichelsonRuntimeError


class ThreeParticipantsDeterminedTest(StateTransformationBaseTest):

    def test_with_three_participants(self):

        self.current_time = RUN_TIME
        self.id = len(self.storage['events'])

        # Trying to create event without providing correct fees:
        amount = self.measure_start_fee + self.expiration_fee
        self.check_new_event_fails_with(
            event_params=self.default_event_params,
            amount=int(amount // 2),
            msg_contains='measureStartFee and expirationFee should be provided')

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

        # Testing that with current ratio 1:1, bet with 10:1 ratio fails:
        self.check_bet_fails_with(
            participant=self.a,
            amount=100_000,
            bet='for',
            minimal_win=1_000_000,
            msg_contains='Wrong minimalWinAmount')

        # Participant B: bets for 50_000 after 1 hour:
        self.current_time = RUN_TIME + ONE_HOUR
        self.storage = self.check_bet_succeed(
            participant=self.b,
            amount=50_000,
            bet='for',
            minimal_win=50_000)

        # Participant A: adding more liquidity after 12 hours
        # (1/2 of the bets period):
        self.current_time = RUN_TIME + 12*ONE_HOUR
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.a,
            amount=50_000,
            expected_for=2,
            expected_against=1)

        # Participant C: adding more liquidity at the very end:
        self.current_time = RUN_TIME + 24*ONE_HOUR
        self.storage = self.check_provide_liquidity_succeed(
            participant=self.c,
            amount=100_000,
            expected_for=1,
            expected_against=1)

        # Running measurement and make failwith checks:
        self.current_time = RUN_TIME + 26*ONE_HOUR
        start_callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time - 1*ONE_HOUR,
            'rate': 6_000_000
        }

        # Checking that it is not possible to run close before measurement started:
        self.check_close_callback_fails_with(
            callback_values=start_callback_values,
            source=self.a,
            sender=self.oracle_address,
            msg_contains="Can't close contract before measurement period started")

        # Checking that measurement with wrong currency pair is failed:
        wrong_callback_currency = start_callback_values.copy()
        wrong_callback_currency.update({'currencyPair': 'WRONG_PAIR'})
        self.check_start_measurement_callback_fails_with(
            callback_values=wrong_callback_currency,
            source=self.a,
            sender=self.oracle_address,
            msg_contains='Unexpected currency pair'
        )
    
        # Check that measurement during bets time is failed:
        callback_in_betstime = start_callback_values.copy()
        callback_in_betstime.update({'lastUpdate': RUN_TIME + 12*ONE_HOUR})
        self.check_start_measurement_callback_fails_with(
            callback_values=callback_in_betstime,
            source=self.a,
            sender=self.oracle_address,
            msg_contains="Can't start measurement untill oracle time"
        )

        # Checking that measurement from wrong address is failed,
        # sender is participant instead of oracle:
        self.check_start_measurement_callback_fails_with(
            callback_values=start_callback_values,
            source=self.a,
            sender=self.a,
            msg_contains='Unknown sender')

        self.storage = self.check_start_measurement_succeed(sender=self.a)

        # Emulating callback:
        self.storage = self.check_start_measurement_callback_succeed(
            callback_values=start_callback_values,
            source=self.a,
            sender=self.oracle_address)

        # Check that betting in measurement period is failed:
        self.check_bet_fails_with(
            participant=self.a,
            amount=100_000,
            bet='against',
            minimal_win=100_000,
            msg_contains='Bets after betCloseTime is not allowed')

        # Check that providing liquidity in measurement period is failed:
        self.check_provide_liquidity_fails_with(
            participant=self.c,
            amount=100_000,
            expected_for=1,
            expected_against=1,
            msg_contains='Providing Liquidity after betCloseTime is not allowed')

        # Check that that calling measurement after it was already succesfully
        # called before is fails:
        self.check_start_measurement_callback_fails_with(
            callback_values=start_callback_values,
            source=self.a,
            sender=self.oracle_address,
            msg_contains='Measurement period already started'
        )

        # Checking that withdrawal before contract is closed is not allowed:
        self.check_withdraw_fails_with(
            participant=self.a,
            withdraw_amount=100_000,
            msg_contains='Withdraw is not allowed until contract is closed')

        # Closing event:
        self.current_time = RUN_TIME + 38*ONE_HOUR
        self.storage = self.check_close_succeed(sender=self.b)

        # Emulating calback with price is increased 25%:
        close_callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time - 1*ONE_HOUR,
            'rate': 7_500_000
        }
        self.storage = self.check_close_callback_succeed(
            callback_values=close_callback_values,
            source=self.b,
            sender=self.oracle_address)

        # Withdrawals:
        self.current_time = RUN_TIME + 64*ONE_HOUR
        self.storage = self.check_withdraw_succeed(self.a, 125_000)
        self.storage = self.check_withdraw_succeed(self.b, 75_000)
        self.storage = self.check_withdraw_succeed(self.c, 100_000)

