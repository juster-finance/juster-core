""" Event: XTZ-USD dynamics would be > 1 in 12 hours after betting period of 24 hours.
    Liquidity pool 0%

    Three participants: a, b and c making next interactions:
        (1) participant A adds initial liquidity at the beginning (0 hours from start): 50k with ratio 1:1
        (2) participant B betAboveEq with 50k (1 hour from start)
            rate at bet 50:100, if S: win amount +25k*L, if ~S: loose amount -50k
            rate after bet 100:25 == 4:1
        (3) participant A adds more liquidity (12 hours from start): 40k with ratio 4:1 (f:a)
        (4) participant C adds more liquidity at the very end (24 hours from start): 80k with ratio 4:1 (f:a)
        (5) particiapnt A calls running_measurement 26 hours from the start
        (6) oracle returns that price at the measurement start is 6.0$ per xtz. Oracle measurement time is behind one hour
        (7) participant B cals close_call at 38 hours from the start
        (8) oracle returns that price at the close is 7.5$ per xtz. Oracle measurement time is behind one hour

    Closed dynamics is +25%, betsAboveEq pool is wins
                                    (1)      (2)      (3)       (4)
    Total event pool:               50_000 + 25_000 + 40_000 +  80_000 = 195_000
    A:                              50_000 + 50_000 + 40_000 +  80_000 = 220_000
    B:                              50_000 - 25_000 + 10_000 +  20_000 =  55_000
            (liquidity rate is not included in the pools)

    if participant B wins he get 50_000 + 25_000 * 100% = 75_000 (this value should be saved in winning amounts ledger)

    Total win S  LP profit / loss:        0 - 25_000 +      0 +       0 = -25_000  (including L bonus for winnig returns)
    Total win ~S LP profit / loss:        0 + 50_000 +      0 +       0 =  50_000  (and not including L bonus for bets)
            (liquidity rate is included in profit/loss pools)

    selected liquidity pool to distribute profits: liquidity Below

    liquidity shares:
        A: 1.4
        C: 0.8

    LP withdraw = Profit/Loss * LP_share + ProvidedL
    A withdraws: -25_000 * 100% + 50_000 + 40_000 = 65_000
    C withdraws: 80_000

    Changes:
        A: 65_000 / 90_000 = 0.722
        B: 75_000 / 50_000 = 1.500
        C: 80_000 / 80_000 = 1.000
"""

from juster_base import (
    JusterBaseTestCase, RUN_TIME, ONE_HOUR)
from pytezos import MichelsonRuntimeError


class ThreeParticipantsDeterminedTest(JusterBaseTestCase):

    def test_with_three_participants(self):

        self.current_time = RUN_TIME
        self.id = self.storage['nextEventId']

        # Trying to create event without providing correct fees:
        amount = self.measure_start_fee + self.expiration_fee
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.new_event(
                event_params=self.default_event_params,
                amount=int(amount // 2))
        msg = 'measureStartFee and expirationFee should be provided'
        self.assertTrue(msg in str(cm.exception))

        # Creating event:
        amount = self.measure_start_fee + self.expiration_fee
        self.new_event(
            event_params=self.default_event_params,
            amount=amount)
        self.assertEqual(self.storage['events'][self.id]['participants'], 0)

        # Participant A: adding liquidity 50/50 just at start:
        self.provide_liquidity(
            participant=self.a,
            amount=50_000,
            expected_above_eq=1,
            expected_below=1)
        self.assertEqual(self.storage['events'][self.id]['participants'], 1)

        # Testing that with current ratio 1:1, bet with 10:1 ratio fails:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.bet(
                participant=self.a,
                amount=100_000,
                bet='aboveEq',
                minimal_win=1_000_000)
        msg = 'Wrong minimalWinAmount'
        self.assertTrue(msg in str(cm.exception))

        # Participant B: bets aboveEq 50_000 after 1 hour:
        self.current_time = RUN_TIME + ONE_HOUR
        self.bet(
            participant=self.b,
            amount=50_000,
            bet='aboveEq',
            minimal_win=50_000)
        self.assertEqual(self.storage['events'][self.id]['participants'], 2)

        # Participant A: adding more liquidity after 12 hours
        # (1/2 of the bets period):
        self.current_time = RUN_TIME + 12*ONE_HOUR
        self.provide_liquidity(
            participant=self.a,
            amount=40_000,
            expected_above_eq=4,
            expected_below=1)
        self.assertEqual(self.storage['events'][self.id]['participants'], 2)

        # Participant C: adding more liquidity at the very end:
        self.current_time = RUN_TIME + 24*ONE_HOUR
        self.provide_liquidity(
            participant=self.c,
            amount=80_000,
            expected_above_eq=4,
            expected_below=1)
        self.assertEqual(self.storage['events'][self.id]['participants'], 3)

        # Running measurement and make failwith checks:
        self.current_time = RUN_TIME + 26*ONE_HOUR
        start_callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time - 1*ONE_HOUR,
            'rate': 6_000_000
        }

        # Checking that it is not possible to run close before measurement started:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.close(
                callback_values=start_callback_values,
                source=self.a,
                sender=self.oracle_address)
        msg = "Can't close contract before measurement period started"
        self.assertTrue(msg in str(cm.exception))

        # Checking that measurement with wrong currency pair is failed:
        wrong_callback_currency = start_callback_values.copy()
        wrong_callback_currency.update({'currencyPair': 'WRONG_PAIR'})

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.start_measurement(
                callback_values=wrong_callback_currency,
                source=self.a,
                sender=self.oracle_address,
            )
        msg = 'Unexpected currency pair'
        self.assertTrue(msg in str(cm.exception))

        # Check that measurement during bets time is failed:
        callback_in_betstime = start_callback_values.copy()
        callback_in_betstime.update({'lastUpdate': RUN_TIME + 12*ONE_HOUR})

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.start_measurement(
                callback_values=callback_in_betstime,
                source=self.a,
                sender=self.oracle_address,
            )
        msg = "Can't start measurement untill oracle time"
        self.assertTrue(msg in str(cm.exception))

        # Checking that measurement from wrong address is failed,
        # sender is participant instead of oracle:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.start_measurement(
                callback_values=start_callback_values,
                source=self.a,
                sender=self.a,
            )
        msg = 'Unknown sender'
        self.assertTrue(msg in str(cm.exception))

        # Emulating callback:
        self.start_measurement(
            callback_values=start_callback_values,
            source=self.a,
            sender=self.oracle_address)

        # Check that betting in measurement period is failed:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.bet(
                participant=self.a,
                amount=100_000,
                bet='below',
                minimal_win=100_000)
        msg = 'Bets after betCloseTime is not allowed'
        self.assertTrue(msg in str(cm.exception))

        # Check that providing liquidity in measurement period is failed:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.provide_liquidity(
                participant=self.c,
                amount=100_000,
                expected_above_eq=1,
                expected_below=1)
        msg = 'Providing Liquidity after betCloseTime is not allowed'
        self.assertTrue(msg in str(cm.exception))

        # Check that that calling measurement after it was already succesfully
        # called before is fails:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.start_measurement(
                callback_values=start_callback_values,
                source=self.a,
                sender=self.oracle_address,
            )
        msg = "Measurement period already started"
        self.assertTrue(msg in str(cm.exception))

        # Checking that withdrawal before contract is closed is not allowed:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.withdraw(
                participant=self.a,
                withdraw_amount=100_000)
        msg = 'Withdraw is not allowed until contract is closed'
        self.assertTrue(msg in str(cm.exception))

        # Closing event:
        self.current_time = RUN_TIME + 38*ONE_HOUR

        # Emulating calback with price is increased 25%:
        close_callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time - 1*ONE_HOUR,
            'rate': 7_500_000
        }
        self.close(
            callback_values=close_callback_values,
            source=self.b,
            sender=self.oracle_address)

        # Trying to trigger Force Majeure is failed because event is closed:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.trigger_force_majeure(sender=self.a)

        # Withdrawals:
        self.assertEqual(self.storage['events'][self.id]['participants'], 3)
        self.current_time = RUN_TIME + 64*ONE_HOUR

        self.withdraw(self.a, 65_000)
        self.assertEqual(self.storage['events'][self.id]['participants'], 2)

        # Another withdrawals:
        self.withdraw(self.b, 75_000)
        self.assertEqual(self.storage['events'][self.id]['participants'], 1)

        # This is last participant, checking that event is removed:
        self.withdraw(self.c, 80_000)
        self.assertFalse(self.id in self.storage['events'])
