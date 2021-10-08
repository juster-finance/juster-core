""" EDGECASE 1 test, different zero-cases """

from juster_base import JusterBaseTestCase, RUN_TIME, ONE_HOUR
from pytezos import MichelsonRuntimeError


class ZeroEdgecasesTest(JusterBaseTestCase):

    def test_zero_edgecases(self):
        self.current_time = RUN_TIME
        self.id = self.storage['nextEventId']

        # Creating event, both fees equal to zero:
        self.measure_start_fee = 0
        self.expiration_fee = 0

        self.storage['config'].update({
            'measureStartFee': self.measure_start_fee,
            'expirationFee': self.expiration_fee,
        })

        self.new_event(
            event_params=self.default_event_params, amount=0)

        # A provides liquidity with 0 tez, assert failed:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.provide_liquidity(
                participant=self.a,
                amount=0,
                expected_above_eq=1,
                expected_below=1)
        self.assertTrue('Zero liquidity provided' in str(cm.exception))

        # A tries to bet but there are no liquidity, assert failed:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.bet(
                participant=self.a,
                amount=1_000_000,
                bet='aboveEq',
                minimal_win=1_000_000)
        msg = "Can't process bet before liquidity added"
        self.assertTrue(msg in str(cm.exception))

        # B provides 10mutez in liquidity with success:
        self.provide_liquidity(
            participant=self.b,
            amount=10,
            expected_above_eq=1,
            expected_below=1)

        # A provides liquidity with 0 expected aboveEq/below, assert failed:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.provide_liquidity(
                participant=self.a,
                amount=1_000_000,
                expected_above_eq=0,
                expected_below=1)
        msg = 'Expected ratio in pool should be more than zero'
        self.assertTrue(msg in str(cm.exception))

        # A tries to adding liquidity with rate that very different from internal rate
        # assert failwith:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.provide_liquidity(
                participant=self.a,
                amount=1_000_000,
                expected_above_eq=10,
                expected_below=1)
        msg = 'Expected ratio very differs from current pool ratio'
        self.assertTrue(msg in str(cm.exception))

        # A provides liquidity with 0 expected aboveEq/below (again), assert failed:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.provide_liquidity(
                participant=self.a,
                amount=1_000_000,
                expected_above_eq=1,
                expected_below=0)
        msg = 'Expected ratio in pool should be more than zero'
        self.assertTrue(msg in str(cm.exception))

        # A tries to Bet with winRate a lot more than expected:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.bet(
                participant=self.a,
                amount=1,
                bet='below',
                minimal_win=5)
        msg = 'Wrong minimalWinAmount'
        self.assertTrue(msg in str(cm.exception))

        # A tries to Bet 0 tez:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.bet(
                participant=self.a,
                amount=0,
                bet='below',
                minimal_win=0)
        msg = 'Bet without tez'
        self.assertTrue(msg in str(cm.exception))

        # In the end: no one bets, starting measure:
        bets_close = self.default_event_params['betsCloseTime']
        period = self.default_event_params['measurePeriod']
        self.current_time = bets_close

        # Emulating callback:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time,
            'rate': 6_000_000
        }

        self.start_measurement(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address)

        # Closing event:
        self.current_time = bets_close + period

        # Emulating calback with price is increased 25%:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': self.current_time,
            'rate': 7_500_000
        }
        self.close(
            callback_values=callback_values,
            source=self.a,
            sender=self.oracle_address)

        # A provides liquidity after event closed is not allowed:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.provide_liquidity(
                participant=self.a,
                amount=10,
                expected_above_eq=1,
                expected_below=1)
        msg = 'Providing Liquidity after betCloseTime is not allowed'
        self.assertTrue(msg in str(cm.exception))

        # Test trying close twice: assert failed:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.close(
                callback_values=callback_values,
                source=self.a,
                sender=self.oracle_address)
        msg = "Event already closed. Can't close event twice"
        self.assertTrue(msg in str(cm.exception))

        # A tries to Bet after event is closed and failed:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.bet(
                participant=self.a,
                amount=1,
                bet='below',
                minimal_win=5)
        msg = 'Bets after betCloseTime is not allowed'
        self.assertTrue(msg in str(cm.exception))

        # test trying to call measurement after close is failed:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.start_measurement(
                callback_values=callback_values,
                source=self.a,
                sender=self.oracle_address)
        msg = 'Measurement period already started'
        self.assertTrue(msg in str(cm.exception))

        # A is not participated so withdraw should fail:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.withdraw(self.a, 0)
        msg = 'Participant not found'
        self.assertTrue(msg in str(cm.exception))

        # B withdraws all:
        self.withdraw(self.b, 10)

        # Test that event was deleted and any interaction would lead to error:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.close(
                callback_values=callback_values,
                source=self.a,
                sender=self.oracle_address)
        msg = "Event is not found"
        self.assertTrue(msg in str(cm.exception))

        with self.assertRaises(MichelsonRuntimeError) as cm:
            self.bet(
                participant=self.a,
                amount=1,
                bet='below',
                minimal_win=5)
        msg = 'Event is not found'
        self.assertTrue(msg in str(cm.exception))

