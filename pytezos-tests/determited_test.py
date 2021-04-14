""" This is simple determined test that interacts with the contract in different
    ways using pytezos intepret method. All interactions splitted into separate blocks.
    After each contract call, new state saved into self.storage and then used in another
    blocks, so block execution order is important. Actually this is one big test.
"""

from pytezos import ContractInterface, pytezos, MichelsonRuntimeError
from unittest import TestCase
from os.path import dirname, join
import time


RUN_TIME = int(time.time())
ONE_HOUR = 60*60
CONTRACT_FN = 'crystal_ball.tz'


class DeterminedTest(TestCase):

    def setUp(self):
        self.contract = ContractInterface.from_file(join(dirname(__file__), CONTRACT_FN))

        # three participants and their pk hashes:
        self.a = 'tz1iQE8ijR5xVPffBUPFubwB9XQJuyD9qsoJ'
        self.b = 'tz1MdaJfWzP5pPx3gwPxfdLZTHW6js9havos'
        self.c = 'tz1RS9GoEXakf9iyBmSaheLMcakFRtzBXpWE'

        self.oracle_address = 'KT1SUP27JhX24Kvr11oUdWswk7FnCW78ZyUn'
        self.currency_pair = 'XTZ-USD'

        self.init_storage = {
            'currencyPair': self.currency_pair,
            'createdTime': RUN_TIME,
            'targetDynamics': 1_000_000,
            'betsCloseTime': RUN_TIME + 24*ONE_HOUR,
            'measureStartTime': 0,
            'measureOracleStartTime': 0,
            'isMeasurementStarted': False,
            'startRate': 0,
            'measurePeriod': 12*ONE_HOUR,
            'isClosed': False,
            'closedTime': 0,
            'closedOracleTime': 0,
            'closedRate': 0,
            'closedDynamics': 0,
            'isBetsForWin': False,

            'betsForLedger': {},
            'betsAgainstLedger': {},
            'liquidityLedger': {},

            'oracleAddress': self.oracle_address,

            'betsForSum': 0,
            'betsAgainstSum': 0,
            'liquiditySum': 0,

            'liquidityPercent': 0,
            'measureStartFee': 200_000,
            'expirationFee': 100_000
        }

        # this self.storage will be used in all blocks:
        self.storage = self.init_storage.copy()


    def _check_result_integrity(self, res):
        """ Checks that sums and ledger values of the resulting storage
            is consistent """

        bets_for_sum = sum(res.storage['betsForLedger'].values())
        self.assertEqual(res.storage['betsForSum'], bets_for_sum)

        bets_against_sum = sum(res.storage['betsAgainstLedger'].values())
        self.assertEqual(res.storage['betsAgainstSum'], bets_against_sum)

        liquidity_sum = sum(res.storage['liquidityLedger'].values())
        self.assertEqual(res.storage['liquiditySum'], liquidity_sum)


    def _participant_A_adds_initial_liquidity(self):
        """ Participant A: adding liquidity 50/50 just at start """

        transaction = self.contract.bet(
            betAgainst=50_000, betFor=50_000).with_amount(100_000)

        res = transaction.interpret(
            storage=self.storage, sender=self.a, now=RUN_TIME)

        self.assertEqual(res.storage['betsForSum'], 50_000)
        self.assertEqual(res.storage['betsAgainstSum'], 50_000)
        self.assertEqual(len(res.storage['betsForLedger']), 1)
        self.assertEqual(len(res.storage['betsAgainstLedger']), 1)
        self.assertEqual(len(res.storage['liquidityLedger']), 1)
        self.assertEqual(res.storage['liquidityLedger'][self.a], 50_000)

        self._check_result_integrity(res)
        self.storage = res.storage

        
    def _assert_wrong_amount_bet(self):
        """ Checking that transaction is fails if amount is not equal to sum
            of the bets / provided liquidity
        """

        with self.assertRaises(MichelsonRuntimeError) as cm:
            transaction = self.contract.bet(betAgainst=0, betFor=50_000).with_amount(100_000)
            res = transaction.interpret(
                storage=self.storage, sender=self.a, now=RUN_TIME)

        self.assertTrue('Sum of bets is not equal to send amount' in str(cm.exception))


    def _participant_B_bets_for(self):
        """ Participant B: bets for 10_000 after 1 hour """

        transaction = self.contract.bet(
            betAgainst=0, betFor=50_000).with_amount(50_000)

        res = transaction.interpret(
            storage=self.storage, sender=self.b, now=RUN_TIME + ONE_HOUR)

        self.assertEqual(res.storage['betsForSum'], 100_000)
        self.assertEqual(res.storage['betsAgainstSum'], 50_000)
        self.assertEqual(len(res.storage['betsForLedger']), 2)
        self.assertEqual(len(res.storage['betsAgainstLedger']), 1)
        self.assertEqual(len(res.storage['liquidityLedger']), 1)

        self._check_result_integrity(res)
        self.storage = res.storage


    def _participant_A_adds_more_liquidity(self):
        """ Participant A: adding more liquidity after 12 hours
            (exactly half of the betting period)
        """

        transaction = self.contract.bet(
            betAgainst=100_000, betFor=50_000).with_amount(150_000)

        res = transaction.interpret(
            storage=self.storage, sender=self.a, now=RUN_TIME + 12*ONE_HOUR)

        self.assertEqual(res.storage['betsForSum'], 150_000)
        self.assertEqual(res.storage['betsAgainstSum'], 150_000)
        self.assertEqual(len(res.storage['betsForLedger']), 2)
        self.assertEqual(len(res.storage['betsAgainstLedger']), 1)
        self.assertEqual(len(res.storage['liquidityLedger']), 1)
        self.assertEqual(res.storage['liquiditySum'], 50_000 + 25_000)

        self._check_result_integrity(res)
        self.storage = res.storage


    def _participant_C_adds_more_liquidity(self):
        """ Participant C: adding more liquidity at the very end """

        transaction = self.contract.bet(
            betAgainst=500_000, betFor=500_000).with_amount(1_000_000)

        res = transaction.interpret(
            storage=self.storage, sender=self.c, now=RUN_TIME + 24*ONE_HOUR)

        self.assertEqual(res.storage['betsForSum'], 650_000)
        self.assertEqual(res.storage['betsAgainstSum'], 650_000)
        self.assertEqual(len(res.storage['betsForLedger']), 3)
        self.assertEqual(len(res.storage['betsAgainstLedger']), 2)
        self.assertEqual(len(res.storage['liquidityLedger']), 2)
        self.assertEqual(res.storage['liquiditySum'], 50_000 + 25_000 + 0)

        self._check_result_integrity(res)
        self.storage = res.storage


    def _assert_closing_before_measurement(self):
        """ Testing that closing before measurement fails """

        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': RUN_TIME + 24*ONE_HOUR,
            'rate': 6_000_000
        }

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.closeCallback(callback_values).interpret(
                storage=self.storage, sender=self.oracle_address, now=RUN_TIME + 24*ONE_HOUR)

        self.assertTrue("Can't close contract before measurement period started" in str(cm.exception))


    def _assert_wrong_currency_pair_return_from_oracle(self):
        """ Testing that wrong currency_pair returned from oracle during measurement is fails """

        callback_values = {
            'currencyPair': 'WRONG_PAIR',
            'lastUpdate': RUN_TIME + 26*ONE_HOUR,
            'rate': 6_000_000
        }

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.startMeasurementCallback(callback_values).interpret(
                storage=self.storage, sender=self.oracle_address, now=RUN_TIME + 26*ONE_HOUR)

        self.assertTrue("Unexpected currency pair" in str(cm.exception))


    def _assert_measurement_during_bets_time(self):
        """ Test that startMeasurement call during bets period is falls """

        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': RUN_TIME + 12*ONE_HOUR,
            'rate': 6_000_000
        }

        with self.assertRaises(MichelsonRuntimeError):
            res = self.contract.startMeasurementCallback(callback_values).interpret(
                storage=self.storage, sender=self.oracle_address, now=RUN_TIME + 12*ONE_HOUR)


    def _running_measurement(self):
        """ Running start measurement after 26 hours """

        res = self.contract.startMeasurement().interpret(
            storage=self.storage, sender=self.a, now=RUN_TIME + 26*ONE_HOUR)

        self.assertEqual(len(res.operations), 1)

        operation = res.operations[0]
        self.assertEqual(operation['destination'], self.oracle_address)
        self.assertEqual(operation['parameters']['entrypoint'], 'get')

        currency_pair = operation['parameters']['value']['args'][0]['string']
        self.assertEqual(currency_pair, self.currency_pair)

        self.assertFalse(res.storage['isMeasurementStarted'])

        self._check_result_integrity(res)
        self.storage = res.storage


    def _assert_callback_from_unknown_address(self):
        """ Assert that callback from unknown address is failed """

        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': RUN_TIME + 26*ONE_HOUR,
            'rate': 6_000_000
        }

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.startMeasurementCallback(callback_values).interpret(
                storage=self.storage, sender=self.c, now=RUN_TIME + 12*ONE_HOUR)

        self.assertTrue('Unknown sender' in str(cm.exception))


    def _measurement_callback(self):
        """ Emulating callback from oracle 26 hours late (but call last value
            in oracle is still from prev hour)
        """

        start_running_time = RUN_TIME + 26*ONE_HOUR
        start_oracle_time = start_running_time - 1*ONE_HOUR

        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': start_oracle_time,
            'rate': 6_000_000
        }

        res = self.contract.startMeasurementCallback(callback_values).interpret(
            storage=self.storage, sender=self.oracle_address,
            now=start_running_time, source=self.a)

        self.assertEqual(len(res.operations), 1)
        self.assertEqual(res.storage['startRate'], callback_values['rate'])
        self.assertTrue(res.storage['isMeasurementStarted'])
        self.assertEqual(res.storage['measureStartTime'], start_running_time)
        self.assertEqual(res.storage['measureOracleStartTime'], start_oracle_time)

        operation = res.operations[0]
        self.assertEqual(operation['destination'], self.a)
        self.assertEqual(int(operation['amount']), self.storage['measureStartFee'])

        self._check_result_integrity(res)
        self.storage = res.storage


    def _assert_betting_in_measurement_period(self):
        """ Test that betting during measurement period is fails """

        with self.assertRaises(MichelsonRuntimeError) as cm:
            transaction = self.contract.bet(
                betAgainst=50_000, betFor=50_000).with_amount(100_000)

            res = transaction.interpret(
                storage=self.storage, sender=self.a, now=RUN_TIME + 28*ONE_HOUR)

        self.assertTrue('Bets after betCloseTime is not allowed' in str(cm.exception))


    def _assert_double_measurement(self):
        """ Test that calling measurement after it was called is fails """

        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': RUN_TIME + 30*ONE_HOUR,
            'rate': 7_000_000
        }

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.startMeasurementCallback(callback_values).interpret(
                storage=self.storage, sender=self.oracle_address, now=RUN_TIME + 30*ONE_HOUR)

        self.assertTrue('Measurement period already started' in str(cm.exception))


    def _close_call(self):
        """ Calling close, should create opearaton with call to oracle get """

        res = self.contract.close().interpret(storage=self.storage, sender=self.b)
        self.assertEqual(len(res.operations), 1)

        operation = res.operations[0]
        self.assertEqual(operation['destination'], self.oracle_address)
        self.assertEqual(operation['parameters']['entrypoint'], 'get')

        currency_pair = operation['parameters']['value']['args'][0]['string']
        self.assertEqual(currency_pair, self.currency_pair)


    def _close_callback(self):
        """ Emulating callback from oracle 38 (24+12+2) hours late (but call last value
            in oracle is still from prev hour)
        """

        close_running_time = RUN_TIME + 38*ONE_HOUR
        close_oracle_time = close_running_time - 1*ONE_HOUR

        # price is increased 25%:
        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': close_oracle_time,
            'rate': 7_500_000
        }

        res = self.contract.closeCallback(callback_values).interpret(
            storage=self.storage, sender=self.oracle_address,
            now=close_running_time, source=self.b)
        self.assertEqual(len(res.operations), 1)
        self.assertEqual(res.storage['closedRate'], callback_values['rate'])
        self.assertTrue(res.storage['isClosed'])
        self.assertTrue(res.storage['isBetsForWin'])
        self.assertEqual(res.storage['closedTime'],  close_running_time)
        self.assertEqual(res.storage['closedOracleTime'], close_oracle_time)

        # dynamic 7.5 / 6.0 is +25%
        self.assertEqual(res.storage['closedDynamics'], 1_250_000)

        operation = res.operations[0]
        self.assertEqual(operation['destination'], self.b)
        self.assertEqual(int(operation['amount']), self.storage['expirationFee'])

        self._check_result_integrity(res)
        self.storage = res.storage


    def test_interactions(self):
        self._participant_A_adds_initial_liquidity()
        self._assert_wrong_amount_bet()
        self._participant_B_bets_for()
        self._participant_A_adds_more_liquidity()
        self._participant_C_adds_more_liquidity()
        self._assert_closing_before_measurement()
        self._assert_wrong_currency_pair_return_from_oracle()
        self._assert_measurement_during_bets_time()
        self._running_measurement()
        self._assert_callback_from_unknown_address()
        self._measurement_callback()
        self._assert_betting_in_measurement_period()
        self._assert_double_measurement()
        self._close_call()
        self._close_callback()

        # TODO: test withdrawals and liquidity bonuses

        # test trying to close twice?
        # test that it is not possible to bet after close?
        # test that it is not possible to call measurement after close
        #    (btw it is tested in double_measurement)
