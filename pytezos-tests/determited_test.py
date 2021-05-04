""" This is simple determined test that interacts with the contract in different
    ways using pytezos intepret method. All interactions splitted into separate blocks.
    After each contract call, new state saved into self.storage and then used in another
    blocks, so block execution order is important. Actually this is one big test.

    Event: XTZ-USD dynamics would be > 1 in 12 hours after betting period of 24 hours.
    Liquidity pool 1%

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
                                      (1)      (2)      (3)      (4)      (5)       (6)
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

from pytezos import ContractInterface, pytezos, MichelsonRuntimeError
from unittest import TestCase
from os.path import dirname, join
import time


RUN_TIME = int(time.time())
ONE_HOUR = 60*60
CONTRACT_FN = 'baking_bet.tz'


def calculate_liquidity_bonus_multiplier(event, current_time):
    close_time = event['betsCloseTime']
    start_time = event['createdTime']
    return (close_time - current_time) / (close_time - start_time)


def calculate_bet_return(top, bottom, amount):
    """ Calculates the amount that would be returned if participant wins
        Not included the bet amount itself, only added value
    """

    ratio = top / (bottom + amount)
    return int(amount * ratio)


def calculate_bet_params_change(event, bet, amount):
    if bet == 'for':
        top = event['betsAgainstLiquidityPoolSum']
        bottom = event['betsForLiquidityPoolSum']

        return dict(
            diff_for=amount,
            diff_against=-calculate_bet_return(top, bottom, amount),
            for_count=1,
            against_count=0
        )

    elif bet == 'against':
        top = event['betsForLiquidityPoolSum']
        bottom = event['betsAgainstLiquidityPoolSum']

        return dict(
            diff_for=-calculate_bet_return(top, bottom, amount),
            diff_against=amount,
            for_count=0,
            against_count=1
        )

    else:
        raise Exception('Wrong bet type')


class StateTransformationTest(TestCase):
    """ Methods used to check different state transformations
        Each check method runs one transaction and then compare storage
        before and after transaction execution. At the end each check
        method returns new storage 
    """

    def assertAmountEqual(self, operation, amount):
        """ Checks that operation amount equals to amount value """

        self.assertEqual(int(operation['amount']), amount)


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


    def _check_result_integrity(self, res, event_id):
        """ Checks that sums and ledger values of the resulting storage
            is consistent """

        def sum_by_id(ledger, _id):
            return sum(value for key, value in ledger.items() if key[1] == _id)

        '''
        bets_for_sum_ledger = sum_by_id(res.storage['betsForLedger'], event_id)
        bets_against_sum_ledger = sum_by_id(res.storage['betsAgainstLedger'], event_id)
        provided_liquidity_sum_ledger = sum_by_id(res.storage['providedLiquidityLedger'], event_id)
        total_ledger_sums = (
            bets_for_sum_ledger + bets_against_sum_ledger + provided_liquidity_sum_ledger)

        bets_for_sum_event = res.storage['events'][event_id]['betsForLiquidityPoolSum']
        bets_against_sum_event = res.storage['events'][event_id]['betsAgainstLiquidityPoolSum']
        # this is a bit confusing now, but provided liquidity is accounted inside bets for / against sums
        # provided_liquidity_sum_event = res.storage['events'][event_id]['totalLiquidityProvided']
        total_event_sums = (
            bets_for_sum_event + bets_against_sum_event)

        self.assertEqual(total_ledger_sums, total_event_sums)
        '''
        # betsForLedger and betsAgainstLedger now contained winnig amounts
        # TODO: need to refactor names to make it clear.
        # and looks like this check is not possible anymore
        pass


    def check_result_integrity(self, result):
        # TODO: Replace this method with actual checks
        pass


    def check_participant_successfully_adds_more_liquidity(
            self, participant, amount, expected_for, expected_against,
            max_slippage=100_000):

        # Running transaction:
        transaction = self.contract.provideLiquidity(
            eventId=self.id,
            expectedRatioAgainst=expected_against,
            expectedRatioFor=expected_for,
            maxSlippage=max_slippage
        ).with_amount(amount)

        # Making variables to compare two states:
        res = transaction.interpret(
            storage=self.storage, sender=participant, now=self.current_time)

        init_storage = self.storage
        result_storage = res.storage

        init_event = init_storage['events'][self.id]
        result_event = result_storage['events'][self.id]

        # Checking that state changed as expected:
        total_liquidity = (init_event['betsForLiquidityPoolSum']
                           + init_event['betsAgainstLiquidityPoolSum'])
        added_for = int(
            amount * init_event['betsForLiquidityPoolSum'] / total_liquidity)
        added_against = int(
            amount * init_event['betsAgainstLiquidityPoolSum'] / total_liquidity)

        difference_for = (result_event['betsForLiquidityPoolSum']
                          - init_event['betsForLiquidityPoolSum'])
        difference_against = (result_event['betsAgainstLiquidityPoolSum']
                              - init_event['betsAgainstLiquidityPoolSum'])

        self.assertEqual(difference_for, added_for)
        self.assertEqual(difference_against, difference_against)

        self.assertEqual(
            len(result_storage['betsForWinningLedger']),
            len(init_storage['betsForWinningLedger']))

        self.assertEqual(
            len(result_storage['betsAgainstWinningLedger']),
            len(init_storage['betsAgainstWinningLedger']))

        # If participant added liquidity before, it should not change
        # ledger records count. If it is not - records should be incresed by 1

        is_already_lp = (participant, self.id) in init_storage['providedLiquidityLedger']
        added_count = 0 if is_already_lp else 1

        self.assertEqual(
            len(result_storage['providedLiquidityLedger']),
            len(init_storage['providedLiquidityLedger']) + added_count)

        self.assertEqual(len(
            result_storage['liquidityForBonusLedger']),
            len(init_storage['liquidityForBonusLedger']) + added_count)

        self.assertEqual(
            len(result_storage['liquidityAgainstBonusLedger']),
            len(init_storage['liquidityAgainstBonusLedger']) + added_count)

        m = calculate_liquidity_bonus_multiplier(init_event, self.current_time)
        self.assertEqual(
            result_event['totalLiquidityForBonusSum'],
            init_event['totalLiquidityForBonusSum'] + int(m*added_for))

        self.assertEqual(
            result_event['totalLiquidityAgainstBonusSum'],
            init_event['totalLiquidityAgainstBonusSum'] + int(m*added_against))

        return result_storage


    def check_participant_successfully_bets(
        self, participant, amount, bet, minimal_win):

        # Running transaction:
        transaction = self.contract.bet(
            eventId=self.id, bet=bet, minimalWinAmount=minimal_win).with_amount(amount)

        res = transaction.interpret(
            storage=self.storage, sender=participant, now=self.current_time)

        # Making variables to compare two states:
        init_storage = self.storage
        result_storage = res.storage

        init_event = init_storage['events'][self.id]
        result_event = result_storage['events'][self.id]

        # Checking that state changed as expected:
        bet_result = calculate_bet_params_change(init_event, bet, amount)

        self.assertEqual(
            result_event['betsForLiquidityPoolSum'],
            init_event['betsForLiquidityPoolSum'] + bet_result['diff_for'])

        self.assertEqual(
            result_event['betsAgainstLiquidityPoolSum'],
            init_event['betsAgainstLiquidityPoolSum'] + bet_result['diff_against'])

        self.assertEqual(
            len(result_storage['betsForWinningLedger']),
            len(init_storage['betsForWinningLedger']) + bet_result['for_count'])

        self.assertEqual(
            len(result_storage['betsAgainstWinningLedger']),
            len(init_storage['betsAgainstWinningLedger']) + bet_result['against_count'])

        # TODO: check sum in participant ledgers (include liquidity fee)
        return result_storage


    def check_participant_succesfully_withdraws(self, participant, withdraw_amount):

        # Running transaction:
        res = self.contract.withdraw(self.id).interpret(
            storage=self.storage, sender=participant, now=self.current_time)

        self.assertAmountEqual(res.operations[0], withdraw_amount)
        # TODO: check scenario with 0 withdrawal (maybe separate method?)
        # TODO: check participant removed from ledgers? (maybe separate method)

        return self.remove_none_values(res.storage)


    def check_event_successfully_created(self):
        # TODO:
        pass

    def check_measurement_start_succesfully_runned(self):
        # TODO:
        pass

    def check_measurement_start_fails_with(self):
        # TODO:
        pass


class DeterminedTest(StateTransformationTest):

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

            'liquidityPercent': 40_000,  # 4% of 1_000_000
            'measureStartFee': self.measure_start_fee,  # who provides it and when?
            'expirationFee': self.expiration_fee
        }

        self.init_storage = {
            'events': {},
            'betsForWinningLedger': {},
            'betsAgainstWinningLedger': {},
            'providedLiquidityLedger': {},
            'liquidityForBonusLedger': {},
            'liquidityAgainstBonusLedger': {},
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
            'betsAgainstLiquidityPoolSum': 0,
            'betsForLiquidityPoolSum': 0,
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


    def _participant_A_adds_initial_liquidity(self):
        """ Participant A: adding liquidity 50/50 just at start """

        transaction = self.contract.provideLiquidity(
            eventId=self.id,
            expectedRatioAgainst=1,
            expectedRatioFor=1,
            maxSlippage=100_000
        ).with_amount(100_000)

        res = transaction.interpret(
            storage=self.storage, sender=self.a, now=RUN_TIME)

        event = res.storage['events'][self.id]
        self.assertEqual(event['betsForLiquidityPoolSum'], 50_000)
        self.assertEqual(event['betsAgainstLiquidityPoolSum'], 50_000)
        self.assertEqual(len(res.storage['betsForWinningLedger']), 0)
        self.assertEqual(len(res.storage['betsAgainstWinningLedger']), 0)
        self.assertEqual(res.storage['liquidityForBonusLedger'][(self.a, self.id)], 50_000)
        self.assertEqual(res.storage['liquidityAgainstBonusLedger'][(self.a, self.id)], 50_000)
        self.assertEqual(res.storage['providedLiquidityLedger'][(self.a, self.id)], 100_000)

        self._check_result_integrity(res, self.id)
        self.storage = res.storage


    def _assert_wrong_ratio_bet(self):
        """ Checking that transaction is fails if amount is not equal to sum
            of the bets / provided liquidity
        """

        # ratio at the call moment 1:1, trying to make a bet with 10:1 ratio:
        with self.assertRaises(MichelsonRuntimeError) as cm:
            transaction = self.contract.bet(
                eventId=self.id, bet='for', minimalWinAmount=1_000_000).with_amount(100_000)
            res = transaction.interpret(
                storage=self.storage, sender=self.a, now=RUN_TIME)

        self.assertTrue('Wrong minimalWinAmount' in str(cm.exception))


    def _participant_B_bets_for(self):
        """ Participant B: bets for 30_000 after 1 hour """

        transaction = self.contract.bet(
            eventId=self.id, bet='for', minimalWinAmount=50_000).with_amount(50_000)

        res = transaction.interpret(
            storage=self.storage, sender=self.b, now=RUN_TIME + ONE_HOUR)

        event = res.storage['events'][self.id]
        self.assertEqual(event['betsForLiquidityPoolSum'], 100_000)
        self.assertEqual(event['betsAgainstLiquidityPoolSum'], 25_000)
        self.assertEqual(len(res.storage['betsForWinningLedger']), 1)
        self.assertEqual(len(res.storage['betsAgainstWinningLedger']), 0)

        self._check_result_integrity(res, self.id)
        self.storage = res.storage


    def _participant_A_adds_more_liquidity(self):
        """ Participant A: adding more liquidity after 12 hours
            (exactly half of the betting period)
        """

        transaction = self.contract.provideLiquidity(
            eventId=self.id,
            expectedRatioAgainst=1,
            expectedRatioFor=2,
            maxSlippage=100_000
        ).with_amount(50_000)

        res = transaction.interpret(
            storage=self.storage, sender=self.a, now=RUN_TIME + 12*ONE_HOUR)

        event = res.storage['events'][self.id]
        # TODO: currently there are round division in contract:
        self.assertEqual(event['betsForLiquidityPoolSum'], 140_000)
        self.assertEqual(event['betsAgainstLiquidityPoolSum'], 35_000)
        self.assertEqual(len(res.storage['betsForWinningLedger']), 1)
        self.assertEqual(len(res.storage['betsAgainstWinningLedger']), 0)
        self.assertEqual(len(res.storage['providedLiquidityLedger']), 1)
        self.assertEqual(len(res.storage['liquidityForBonusLedger']), 1)
        self.assertEqual(len(res.storage['liquidityAgainstBonusLedger']), 1)

        # the next sums are possible to be changed if not linear coef will be
        # used to decrease liquidity bonus:
        self.assertEqual(event['totalLiquidityForBonusSum'], 50_000 + 20_000)
        self.assertEqual(event['totalLiquidityAgainstBonusSum'], 50_000 + 5_000)

        self._check_result_integrity(res, self.id)
        self.storage = res.storage


    def _participant_D_adds_more_liquidity(self):
        """ Participant D: adding more liquidity after 12 hours
            (exactly half of the betting period) """

        self.current_time = RUN_TIME + 12*ONE_HOUR
        self.storage = self.check_participant_successfully_adds_more_liquidity(
            participant=self.d, amount=450_000, expected_for=4, expected_against=1)


    def _participant_D_bets_against(self):
        """ Participant D: bets against 125_000 after 1 hour """

        self.current_time = RUN_TIME + 12*ONE_HOUR
        self.storage = self.check_participant_successfully_bets(
            participant=self.d, amount=125_000, bet='against', minimal_win=125_000)


    def _participant_C_adds_more_liquidity(self):
        """ Participant C: adding more liquidity at the very end """

        self.current_time = RUN_TIME + 24*ONE_HOUR
        self.storage = self.check_participant_successfully_adds_more_liquidity(
            participant=self.c, amount=100_000, expected_for=1, expected_against=1)


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
                eventId=self.id, bet='against', minimalWinAmount=100_000).with_amount(100_000)

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
        self.assertEqual(event['closedOracleTime'], close_oracle_time)

        # dynamic 7.5 / 6.0 is +25%
        self.assertEqual(event['closedDynamics'], 1_250_000)

        operation = res.operations[0]
        self.assertEqual(operation['destination'], self.b)
        self.assertAmountEqual(operation, self.expiration_fee)

        self._check_result_integrity(res, self.id)
        self.storage = res.storage


    def _withdrawals_check_scenario_without_D(self):
        """ Checking that all withdrawals calculated properly
                (scenaro with 3 participants):
            A: 126_000
            B: 74_000
            C: 100_000
        """

        self.current_time = RUN_TIME + 64*ONE_HOUR
        self.storage = self.check_participant_succesfully_withdraws(self.a, 126_000)
        self.storage = self.check_participant_succesfully_withdraws(self.b, 74_000)
        self.storage = self.check_participant_succesfully_withdraws(self.c, 100_000)


    def _withdrawals_check_scenario_with_D(self):
        """ Checking that all withdrawals calculated properly
                (scenaro with 4 participants):
            A: 205_550 / 150_000 = 1.370
            B:  74_000 /  50_000 = 1.480
            C: 100_000 / 100_000 = 1.000
            D: 495_450 / 575_000 = 0.862
        """

        self.current_time = RUN_TIME + 64*ONE_HOUR
        self.storage = self.check_participant_succesfully_withdraws(self.a, 205_550)
        self.storage = self.check_participant_succesfully_withdraws(self.b, 74_000)
        self.storage = self.check_participant_succesfully_withdraws(self.c, 100_000)
        self.storage = self.check_participant_succesfully_withdraws(self.d, 495_450)


    def _scenario_without_D(self):
        """ Test for 3 participants without D """

        self._create_event()
        self._create_evet_with_conflict_fees()
        self._create_more_events()
        self._participant_A_adds_initial_liquidity()
        self._assert_wrong_ratio_bet()
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
        self._withdrawals_check_scenario_without_D()


    def _scenario_with_D(self):
        """ Test for 3 participants without D """

        self._create_event()
        self._participant_A_adds_initial_liquidity()
        self._participant_B_bets_for()
        self._participant_A_adds_more_liquidity()
        self._participant_D_adds_more_liquidity()
        self._participant_D_bets_against()
        self._participant_C_adds_more_liquidity()
        self._running_measurement()
        self._measurement_callback()
        self._close_call()
        self._close_callback()
        self._withdrawals_check_scenario_with_D()


    def test_interactions(self):
        self.id = 0
        # self._scenario_without_D()

        # self.id = 1
        self._scenario_with_D()

        # TODO: make more simple / edge scenarios from this pieces:
        #     - no LP no bets (but try to make bets, should fail)
        #     - one LP no bets at all
        #     - one LP and one bet

        # TODO: make next tests inside some / all scenarios:
        # -- (!) two participants distribute some liquidity (
        #      maybe replace participant A in second liquidity addition
        #      with D and create different scenario?)

        # test trying to close twice?
        # test that it is not possible to bet after close?
        # test that it is not possible to call measurement after close
        #    (btw it is tested in double_measurement)
        # TODO: check that after event no records are left and all cleaned up

        # TODO: make this tests for two - three ids in cycle?
        # TODO: provide liquidity tests:
        # -- (1) adding liquidity with expected rate
        # -- (2) adding liquidity with rate that different from internal rate
        # TODO: test Bet with winRate less than expected (assert MichelsonError raises)
        # TODO: test that adding liquidity after bets time is not allowed
        # TODO: test where one of the participants is LP at the same time
        # TODO: test that LP can withdraw instead of participant after some time
        #    -- test that LP can't withdraw instead of participant before this time
        # TODO: test scenario when LP have profits (current scenario: LP have losses)
        # TODO: test that LP can't withdraw while there are some participants
        # TODO: test that it is not possible to make a bet, that would overflow
        #    some of the pools (For or Against) (so they exceed total liquidity provided)

        # TODO: make this test inside sandbox

