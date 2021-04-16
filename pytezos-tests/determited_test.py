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
        self.measure_start_fee = 200_000
        self.expiration_fee = 100_000

        # this is eventId that for the tests:
        self.id = 0

        self.event = {
            'currencyPair': self.currency_pair,
            'targetDynamics': 1_000_000,
            'betsCloseTime': RUN_TIME + 24*ONE_HOUR,
            'measurePeriod': 12*ONE_HOUR,
            'oracleAddress': self.oracle_address,

            'liquidityPercent': 10_000,  # 1% of 1_000_000
            'measureStartFee': self.measure_start_fee,  # who provides it and when?
            'expirationFee': self.expiration_fee
        }

        self.init_storage = {
            'events': {},
            'betsForLedger': {},
            'betsAgainstLedger': {},
            'liquidityLedger': {},
            'lastEventId': 0,
            'closeCallEventId': None,
            'measurementStartCallEventId': None
        }

        # this self.storage will be used in all blocks:
        self.storage = self.init_storage.copy()


    def _create_event(self):
        """ Testing creating event with settings that should succeed """

        amount = self.measure_start_fee + self.expiration_fee
        result = self.contract.newEvent(self.event).with_amount(amount).interpret(
            now=RUN_TIME, storage=self.storage)

        self.storage = result.storage
        event = result.storage['events'][self.id]

        # Not all event parameters need to be tested, some of them can have any
        # value at the moment of creation:
        proper_event = self.event.copy()
        proper_event.update({
            'betsAgainstSum': 0,
            'betsForSum': 0,
            'isClosed': False,
            'isMeasurementStarted': False,
        })

        selected_event_keys = {k: v for k, v in event.items() if k in proper_event}
        self.assertDictEqual(proper_event, selected_event_keys)


    def _create_evet_with_conflict_fees(self):
        """ Testing that event creation with provided amount less than
            measureStartFee + expirationFee leads to error
        """
        # TODO:
        pass


    def _create_more_events(self):
        """ Testing multiple events creation """
        # TODO:
        pass


    def remove_none_values(self, storage):
        """ Processes storage and removes all none values from bigmaps. They arises
            when item was removed from bigmap during interpret and it cause michelson errors
            when trying to transfer this storage to another interpret
        """

        def clean_dict(dct):
            return {key: value for key, value in dct.items() if value}

        return {
            key: clean_dict(value) if type(value) is dict else value
            for key, value in storage.items()
        }


    def assertAmountEqual(self, operation, amount):
        """ Checks that operation amount equals to amount value """

        self.assertEqual(int(operation['amount']), amount)


    def _check_result_integrity(self, res, event_id):
        """ Checks that sums and ledger values of the resulting storage
            is consistent """

        def sum_by_id(ledger, _id):
            return sum(value for key, value in ledger.items() if key[1] == _id)

        bets_for_sum_ledger = sum_by_id(res.storage['betsForLedger'], event_id)
        bets_for_sum_event = res.storage['events'][event_id]['betsForSum']
        self.assertEqual(bets_for_sum_event, bets_for_sum_ledger)

        bets_against_sum_ledger = sum_by_id(res.storage['betsAgainstLedger'], event_id)
        bets_against_sum_event = res.storage['events'][event_id]['betsAgainstSum']
        self.assertEqual(bets_against_sum_event, bets_against_sum_ledger)

        liquidity_sum_ledger = sum_by_id(res.storage['liquidityLedger'], event_id)
        liquidity_sum_event = res.storage['events'][event_id]['liquiditySum']
        self.assertEqual(liquidity_sum_event, liquidity_sum_ledger)


    def _participant_A_adds_initial_liquidity(self):
        """ Participant A: adding liquidity 50/50 just at start """

        transaction = self.contract.bet(
            eventId=self.id, betAgainst=50_000, betFor=50_000).with_amount(100_000)

        res = transaction.interpret(
            storage=self.storage, sender=self.a, now=RUN_TIME)

        event = res.storage['events'][self.id]
        self.assertEqual(event['betsForSum'], 50_000)
        self.assertEqual(event['betsAgainstSum'], 50_000)
        self.assertEqual(len(res.storage['betsForLedger']), 1)
        self.assertEqual(len(res.storage['betsAgainstLedger']), 1)
        self.assertEqual(len(res.storage['liquidityLedger']), 1)
        self.assertEqual(res.storage['liquidityLedger'][(self.a, self.id)], 50_000)

        self._check_result_integrity(res, self.id)
        self.storage = res.storage

        
    def _assert_wrong_amount_bet(self):
        """ Checking that transaction is fails if amount is not equal to sum
            of the bets / provided liquidity
        """

        with self.assertRaises(MichelsonRuntimeError) as cm:
            transaction = self.contract.bet(
                eventId=self.id, betAgainst=0, betFor=50_000).with_amount(100_000)
            res = transaction.interpret(
                storage=self.storage, sender=self.a, now=RUN_TIME)

        self.assertTrue('Sum of bets is not equal to send amount' in str(cm.exception))


    def _participant_B_bets_for(self):
        """ Participant B: bets for 10_000 after 1 hour """

        transaction = self.contract.bet(
            eventId=self.id, betAgainst=0, betFor=50_000).with_amount(50_000)

        res = transaction.interpret(
            storage=self.storage, sender=self.b, now=RUN_TIME + ONE_HOUR)

        event = res.storage['events'][self.id]
        self.assertEqual(event['betsForSum'], 100_000)
        self.assertEqual(event['betsAgainstSum'], 50_000)
        self.assertEqual(len(res.storage['betsForLedger']), 2)
        self.assertEqual(len(res.storage['betsAgainstLedger']), 1)
        self.assertEqual(len(res.storage['liquidityLedger']), 1)

        self._check_result_integrity(res, self.id)
        self.storage = res.storage


    def _participant_A_adds_more_liquidity(self):
        """ Participant A: adding more liquidity after 12 hours
            (exactly half of the betting period)
        """

        transaction = self.contract.bet(
            eventId=self.id, betAgainst=100_000, betFor=50_000).with_amount(150_000)

        res = transaction.interpret(
            storage=self.storage, sender=self.a, now=RUN_TIME + 12*ONE_HOUR)

        event = res.storage['events'][self.id]
        self.assertEqual(event['betsForSum'], 150_000)
        self.assertEqual(event['betsAgainstSum'], 150_000)
        self.assertEqual(len(res.storage['betsForLedger']), 2)
        self.assertEqual(len(res.storage['betsAgainstLedger']), 1)
        self.assertEqual(len(res.storage['liquidityLedger']), 1)
        self.assertEqual(event['liquiditySum'], 50_000 + 25_000)

        self._check_result_integrity(res, self.id)
        self.storage = res.storage


    def _participant_C_adds_more_liquidity(self):
        """ Participant C: adding more liquidity at the very end """

        transaction = self.contract.bet(
            eventId=self.id, betAgainst=500_000, betFor=500_000).with_amount(1_000_000)

        res = transaction.interpret(
            storage=self.storage, sender=self.c, now=RUN_TIME + 24*ONE_HOUR)

        event = res.storage['events'][self.id]
        self.assertEqual(event['betsForSum'], 650_000)
        self.assertEqual(event['betsAgainstSum'], 650_000)
        self.assertEqual(len(res.storage['betsForLedger']), 3)
        self.assertEqual(len(res.storage['betsAgainstLedger']), 2)
        self.assertEqual(len(res.storage['liquidityLedger']), 2)
        self.assertEqual(event['liquiditySum'], 50_000 + 25_000 + 0)

        self._check_result_integrity(res, self.id)
        self.storage = res.storage


    def _assert_closing_before_measurement(self):
        """ Testing that closing before measurement fails """

        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': RUN_TIME + 24*ONE_HOUR,
            'rate': 6_000_000
        }

        result = self.contract.close(self.id).interpret(
            storage=self.storage, sender=self.a, now=RUN_TIME + 24*ONE_HOUR)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.closeCallback(callback_values).interpret(
                storage=result.storage, sender=self.oracle_address, now=RUN_TIME + 24*ONE_HOUR)

        self.assertTrue("Can't close contract before measurement period started" in str(cm.exception))


    def _assert_wrong_currency_pair_return_from_oracle(self):
        """ Testing that wrong currency_pair returned from oracle during measurement is fails """

        callback_values = {
            'currencyPair': 'WRONG_PAIR',
            'lastUpdate': RUN_TIME + 26*ONE_HOUR,
            'rate': 6_000_000
        }

        result = self.contract.startMeasurement(self.id).interpret(
            storage=self.storage, sender=self.a, now=RUN_TIME + 24*ONE_HOUR)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.startMeasurementCallback(callback_values).interpret(
                storage=result.storage, sender=self.oracle_address, now=RUN_TIME + 26*ONE_HOUR)

        self.assertTrue("Unexpected currency pair" in str(cm.exception))


    def _assert_measurement_during_bets_time(self):
        """ Test that startMeasurement call during bets period is falls """

        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': RUN_TIME + 12*ONE_HOUR,
            'rate': 6_000_000
        }

        result = self.contract.startMeasurement(self.id).interpret(
            storage=self.storage, sender=self.a, now=RUN_TIME + 24*ONE_HOUR)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.startMeasurementCallback(callback_values).interpret(
                storage=result.storage, sender=self.oracle_address, now=RUN_TIME + 12*ONE_HOUR)

        self.assertTrue("Can't start measurement untill betsCloseTime" in str(cm.exception))


    def _running_measurement(self):
        """ Running start measurement after 26 hours """

        res = self.contract.startMeasurement(self.id).interpret(
            storage=self.storage, sender=self.a, now=RUN_TIME + 26*ONE_HOUR)

        self.assertEqual(len(res.operations), 1)

        operation = res.operations[0]
        self.assertEqual(operation['destination'], self.oracle_address)
        self.assertEqual(operation['parameters']['entrypoint'], 'get')

        currency_pair = operation['parameters']['value']['args'][0]['string']
        self.assertEqual(currency_pair, self.currency_pair)

        event = res.storage['events'][self.id]
        self.assertFalse(event['isMeasurementStarted'])

        self._check_result_integrity(res, self.id)
        self.storage = res.storage


    def _assert_callback_from_unknown_address(self):
        """ Assert that callback from unknown address is failed """

        callback_values = {
            'currencyPair': self.currency_pair,
            'lastUpdate': RUN_TIME + 26*ONE_HOUR,
            'rate': 6_000_000
        }

        result = self.contract.startMeasurement(self.id).interpret(
            storage=self.storage, sender=self.a, now=RUN_TIME + 24*ONE_HOUR)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.startMeasurementCallback(callback_values).interpret(
                storage=result.storage, sender=self.c, now=RUN_TIME + 12*ONE_HOUR)

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

        self.assertEqual(self.storage['measurementStartCallEventId'], self.id)
        res = self.contract.startMeasurementCallback(callback_values).interpret(
            storage=self.storage, sender=self.oracle_address,
            now=start_running_time, source=self.a)

        self.assertEqual(len(res.operations), 1)
        event = res.storage['events'][self.id]

        self.assertEqual(event['startRate'], callback_values['rate'])
        self.assertTrue(event['isMeasurementStarted'])
        self.assertEqual(event['measureStartTime'], start_running_time)
        self.assertEqual(event['measureOracleStartTime'], start_oracle_time)

        operation = res.operations[0]
        self.assertEqual(operation['destination'], self.a)
        self.assertAmountEqual(operation, self.measure_start_fee)

        self._check_result_integrity(res, self.id)
        self.storage = res.storage


    def _assert_betting_in_measurement_period(self):
        """ Test that betting during measurement period is fails """

        with self.assertRaises(MichelsonRuntimeError) as cm:
            transaction = self.contract.bet(
                eventId=self.id, betAgainst=50_000, betFor=50_000).with_amount(100_000)

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

        result = self.contract.startMeasurement(self.id).interpret(
            storage=self.storage, sender=self.a, now=RUN_TIME + 24*ONE_HOUR)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.startMeasurementCallback(callback_values).interpret(
                storage=result.storage, sender=self.oracle_address, now=RUN_TIME + 30*ONE_HOUR)

        self.assertTrue('Measurement period already started' in str(cm.exception))


    def _assert_withdraw_before_close(self):
        """ Test that withdraw before close raises error """

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.withdraw(self.id).interpret(
                storage=self.storage, sender=self.a, now=RUN_TIME + 30*ONE_HOUR)

        self.assertTrue('Withdraw is not allowed until contract is closed' in str(cm.exception))


    def _close_call(self):
        """ Calling close, should create opearaton with call to oracle get """

        res = self.contract.close(self.id).interpret(
            storage=self.storage, sender=self.b, now=RUN_TIME + 38*ONE_HOUR)
        self.assertEqual(len(res.operations), 1)

        operation = res.operations[0]
        self.assertEqual(operation['destination'], self.oracle_address)
        self.assertEqual(operation['parameters']['entrypoint'], 'get')

        currency_pair = operation['parameters']['value']['args'][0]['string']
        self.assertEqual(currency_pair, self.currency_pair)

        self._check_result_integrity(res, self.id)
        self.storage = res.storage


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

        event = res.storage['events'][self.id]
        self.assertEqual(event['closedRate'], callback_values['rate'])
        self.assertTrue(event['isClosed'])
        self.assertTrue(event['isBetsForWin'])
        self.assertEqual(event['closedTime'],  close_running_time)
        self.assertEqual(event['closedOracleTime'], close_oracle_time)

        # dynamic 7.5 / 6.0 is +25%
        self.assertEqual(event['closedDynamics'], 1_250_000)

        operation = res.operations[0]
        self.assertEqual(operation['destination'], self.b)
        self.assertAmountEqual(operation, self.expiration_fee)

        self._check_result_integrity(res, self.id)
        self.storage = res.storage


    def _assert_losing_participant_withdraw(self):
        """ Checking that loosed / not participated address cannot withdraw """

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.withdraw(self.id).interpret(
                storage=self.storage, sender=self.d, now=RUN_TIME + 64*ONE_HOUR)

        self.assertTrue('Nothing to withdraw' in str(cm.exception))


    def _withdrawals_check(self):
        """ Checking that all withdrawals calculated properly:
            A: 15.3846% * 1_287_000 + 100% * 13_000 = 211_000
            B: 7.6923% * 1_287_000 + 0% * 13_000 = 99_000
            C: 76.9231% * 1_287_000 + 0% * 13_000 = 990_000
        """

        # A withdraws:
        res = self.contract.withdraw(self.id).interpret(
            storage=self.storage, sender=self.a, now=RUN_TIME + 64*ONE_HOUR)
        self.assertAmountEqual(res.operations[0], 211_000)
        self.storage = self.remove_none_values(res.storage)

        # B withdraws:
        res = self.contract.withdraw(self.id).interpret(
            storage=self.storage, sender=self.b, now=RUN_TIME + 64*ONE_HOUR)
        self.assertAmountEqual(res.operations[0], 99_000)
        self.storage = self.remove_none_values(res.storage)

        # C withdraws:
        res = self.contract.withdraw(self.id).interpret(
            storage=self.storage, sender=self.c, now=RUN_TIME + 64*ONE_HOUR)
        self.assertAmountEqual(res.operations[0], 990_000)
        self.storage = self.remove_none_values(res.storage)


    def _assert_double_withdrawal(self):
        """ Participant A tries to withdraw second time, should get error that
            nothing to withdraw """

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.withdraw(self.id).interpret(
                storage=self.storage, sender=self.a, now=RUN_TIME + 64*ONE_HOUR)

        self.assertTrue('Nothing to withdraw' in str(cm.exception))


    def _run_all_tests(self):
        self._create_event()
        self._create_evet_with_conflict_fees()
        self._create_more_events()
        self._participant_A_adds_initial_liquidity()
        self._assert_wrong_amount_bet()
        self._participant_B_bets_for()
        self._participant_A_adds_more_liquidity()
        self._participant_C_adds_more_liquidity()
        self._assert_closing_before_measurement()
        self._assert_wrong_currency_pair_return_from_oracle()
        self._assert_measurement_during_bets_time()
        self._assert_callback_from_unknown_address()
        self._running_measurement()
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

        # TODO: make this tests for two - three ids in cycle?


    def test_interactions(self):
        for some_id in range(3):
            self.id = some_id
            self._run_all_tests()
