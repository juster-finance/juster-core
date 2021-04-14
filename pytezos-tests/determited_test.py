""" This is simple determined test that interacts with the contract in different
    ways using pytezos intepret method. All interactions splitted into separate blocks.
    After each contract call, new state saved into self.storage and then used in another
    blocks, so block execution order is important. Actually this is one big test.

    Event: XTZ-USD dynamics would be > 1 in 12 hours after betting period of 24 hours.
    Liquidity pool 1%

    Three participants: a, b and c making next interactions:
        - participant A adds initial liquidity at the beginning (0 hours from start): betAgainst=50_000, betFor=50_000
        - participant B betFor with 50_000 (1 hour from start)
        - participant A adds more liquidity (12 hours from start): betAgainst=100_000, betFor=50_000
        - participant C adds more liquidity at the very end (24 hours from start): betAgainst=500_000, betFor=500_000
        - particiapnt A calls running_measurement 26 hours from the start
        - oracle returns that price at the measurement start is 6.0$ per xtz. Oracle measurement time is behind one hour
        - participant B cals close_call at 38 hours from the start
        - oracle returns that price at the close is 7.5$ per xtz. Oracle measurement time is behind one hour

    Closed dynamics is +25%, betsFor pool is wins
    Total bets: 50_000 + 50_000 + 50_000 + 100_000 + 50_000 + 500_000 + 500_000 = 1_300_000
    Total betsFor: 50_000 + 50_000 + 50_000 + 500_000 = 650_000
    Total liquidity bonuses: 50_000 * 1 + 50_000 * 0.5 + 500_000 * 0 = 75_000

    betsFor shares:
        A: 100_000 / 650_000 = 15.3846%
        B: 50_000 / 650_000 = 7.6923%
        C: 500_000 / 650_000 = 76.9231%

    Liquidity shares:
        A: 75_000 / 75_000 = 100%
        B: 0 / 75_000 = 0%
        C: 500_000 * 0 / 75_000 = 0%

    Winning pool: 1_300_000 * 99% = 1_287_000
    Liquidity pool: 1_300_000 * 1% = 13_000

    withdraw amounts:
        A: 15.3846% * 1_287_000 + 100% * 13_000 = 211_000
        B: 7.6923% * 1_287_000 + 0% * 13_000 = 99_000
        C: 76.9231% * 1_287_000 + 0% * 13_000 = 990_000

    Changes:
        A: 211_000 / 250_000 = 0.844
        B: 99_000 / 50_000 = 1.980
        C: 990_000 / 1_000_000 = 0.990

    A - made a lot betAgainst and loose it to B
    B - wins all that A looses
    C - just paid for liquidity because his addition at the end does not matter

    NOTE: measure start and expiration fees is not taken into account here
    TODO: need to determine which solution with fees is better (who and when provides it)
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
        self.d = 'tz1TdKuFwYgbPHHb7y1VvLH4xiwtAzcjwDjM'

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

            'liquidityPercent': 10_000,  # 1% of 1_000_000
            'measureStartFee': 200_000,  # who provides it and when?
            'expirationFee': 100_000
        }

        # this self.storage will be used in all blocks:
        self.storage = self.init_storage.copy()


    def remove_none_values(self, storage):
        """ Processes storage and removes all none values from bigmaps. They arises
            when item was removed from bigmap during interpret and it cause michelson errors
            when trying to transfer this storage to another interpret
        """

        return {
            key: self.remove_none_values(value) if type(value) is dict else value
            for key, value in storage.items() if value is not None
        }


    def assertAmountEqual(self, operation, amount):
        """ Checks that operation amount equals to amount value """

        self.assertEqual(int(operation['amount']), amount)


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
        self.assertAmountEqual(operation, self.storage['measureStartFee'])

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


    def _assert_withdraw_before_close(self):
        """ Test that withdraw before close raises error """

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.withdraw().interpret(
                storage=self.storage, sender=self.a, now=RUN_TIME + 30*ONE_HOUR)

        self.assertTrue('Withdraw is not allowed until contract is closed' in str(cm.exception))


    def _close_call(self):
        """ Calling close, should create opearaton with call to oracle get """

        res = self.contract.close().interpret(
            storage=self.storage, sender=self.b, now=RUN_TIME + 38*ONE_HOUR)
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
        self.assertAmountEqual(operation, self.storage['expirationFee'])

        self._check_result_integrity(res)
        self.storage = res.storage


    def _assert_losing_participant_withdraw(self):
        """ Checking that loosed / not participated address cannot withdraw """

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.withdraw().interpret(
                storage=self.storage, sender=self.d, now=RUN_TIME + 64*ONE_HOUR)

        self.assertTrue('Nothing to withdraw' in str(cm.exception))


    def _withdrawals_check(self):
        """ Checking that all withdrawals calculated properly:
            A: 15.3846% * 1_287_000 + 100% * 13_000 = 211_000
            B: 7.6923% * 1_287_000 + 0% * 13_000 = 99_000
            C: 76.9231% * 1_287_000 + 0% * 13_000 = 990_000
        """

        # A withdraws:
        res = self.contract.withdraw().interpret(
            storage=self.storage, sender=self.a, now=RUN_TIME + 64*ONE_HOUR)
        self.assertAmountEqual(res.operations[0], 211_000)
        self.storage = self.remove_none_values(res.storage)

        # B withdraws:
        res = self.contract.withdraw().interpret(
            storage=self.storage, sender=self.b, now=RUN_TIME + 64*ONE_HOUR)
        self.assertAmountEqual(res.operations[0], 99_000)
        self.storage = self.remove_none_values(res.storage)

        # C withdraws:
        res = self.contract.withdraw().interpret(
            storage=self.storage, sender=self.c, now=RUN_TIME + 64*ONE_HOUR)
        self.assertAmountEqual(res.operations[0], 990_000)
        self.storage = self.remove_none_values(res.storage)


    def _assert_double_withdrawal(self):
        """ Participant A tries to withdraw second time, should get error that
            nothing to withdraw """

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.withdraw().interpret(
                storage=self.storage, sender=self.a, now=RUN_TIME + 64*ONE_HOUR)

        self.assertTrue('Nothing to withdraw' in str(cm.exception))


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
        self._assert_withdraw_before_close()
        self._close_call()
        self._close_callback()
        self._assert_losing_participant_withdraw()
        self._withdrawals_check()
        self._assert_double_withdrawal()

        # TODO: test withdrawals and liquidity bonuses

        # test trying to close twice?
        # test that it is not possible to bet after close?
        # test that it is not possible to call measurement after close
        #    (btw it is tested in double_measurement)
