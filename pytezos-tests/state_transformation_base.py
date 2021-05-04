""" This is base class that used in different tests. 
    It uses pytezos intepret method.
    Each entrypoint call implemented in separate methods:
        one for success and possible some with failwith.
    After each contract call, new state returned and then saved into self.storage
    so it can be used in another blocks.
    TODO: try to move all this interactions inside sandbox
"""

from unittest import TestCase
import time
from os.path import dirname, join
from pytezos import ContractInterface, pytezos, MichelsonRuntimeError


CONTRACT_FN = 'baking_bet.tz'
RUN_TIME = int(time.time())
ONE_HOUR = 60*60


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


class StateTransformationBaseTest(TestCase):
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


    """ Test blocks for provideLiquidity entrypoint: """
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
        result = transaction.interpret(
            storage=self.storage, sender=participant, now=self.current_time)

        init_storage = self.storage
        result_storage = result.storage

        init_event = init_storage['events'][self.id]
        result_event = result_storage['events'][self.id]

        # Checking that state changed as expected:
        total_liquidity = (init_event['betsForLiquidityPoolSum']
                           + init_event['betsAgainstLiquidityPoolSum'])

        if total_liquidity > 0:
            added_for_share = (
                init_event['betsForLiquidityPoolSum'] / total_liquidity)
            added_against_share = (
                init_event['betsAgainstLiquidityPoolSum'] / total_liquidity)

        else:
            added_for_share = (
                expected_for / (expected_for + expected_against))
            added_against_share = (
                expected_against / (expected_for + expected_against))

        added_for = int(amount * added_for_share)
        added_against = int(amount * added_against_share)

        difference_for = (result_event['betsForLiquidityPoolSum']
                          - init_event['betsForLiquidityPoolSum'])
        difference_against = (result_event['betsAgainstLiquidityPoolSum']
                              - init_event['betsAgainstLiquidityPoolSum'])

        self.assertEqual(difference_for, added_for)
        self.assertEqual(difference_against, added_against)

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

        self._check_result_integrity(result, self.id)
        return result_storage


    """ Test blocks for bet entrypoint: """
    def check_participant_successfully_bets(
            self, participant, amount, bet, minimal_win):

        # Running transaction:
        transaction = self.contract.bet(
            eventId=self.id, bet=bet, minimalWinAmount=minimal_win).with_amount(amount)

        result = transaction.interpret(
            storage=self.storage, sender=participant, now=self.current_time)

        # Making variables to compare two states:
        init_storage = self.storage
        result_storage = result.storage

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

        self._check_result_integrity(result, self.id)
        return result_storage


    def check_wrong_ratio_bet_is_failed(
            self, participant, amount, bet, minimal_win):
        """ Checking that transaction is fails if the bet ratio is too different
            from ratio in current pool
        """

        with self.assertRaises(MichelsonRuntimeError) as cm:
            transaction = self.contract.bet(
                eventId=self.id,
                bet='for',
                minimalWinAmount=minimal_win
            ).with_amount(amount)

            res = transaction.interpret(
                storage=self.storage,
                sender=participant,
                now=self.current_time)

        self.assertTrue('Wrong minimalWinAmount' in str(cm.exception))


    def check_betting_in_measurement_period_is_failed(
            self, participant, amount, bet, minimal_win):
        """ Test that betting during measurement period is fails """

        with self.assertRaises(MichelsonRuntimeError) as cm:
            transaction = self.contract.bet(
                eventId=self.id,
                bet=bet,
                minimalWinAmount=minimal_win
            ).with_amount(amount)

            res = transaction.interpret(
                storage=self.storage,
                sender=participant,
                now=self.current_time)

        self.assertTrue('Bets after betCloseTime is not allowed' in str(cm.exception))


    """ Test blocks for withdraw entrypoint: """
    def check_participant_succesfully_withdraws(self, participant, withdraw_amount):

        # Running transaction:
        result = self.contract.withdraw(self.id).interpret(
            storage=self.storage, sender=participant, now=self.current_time)

        # Checking that state changed as expected:
        self.assertAmountEqual(result.operations[0], withdraw_amount)
        # TODO: check scenario with 0 withdrawal (maybe separate method?)
        # TODO: check participant removed from ledgers? (maybe separate method)

        self._check_result_integrity(result, self.id)
        return self.remove_none_values(result.storage)


    """ Test blocks for newEvent entrypoint: """
    def check_event_successfully_created(self, event_params, amount):
        """ Testing creating event with settings that should succeed """

        # Running transaction:
        result = self.contract.newEvent(event_params).with_amount(amount).interpret(
            now=RUN_TIME, storage=self.storage, amount=amount)

        # Making variables to compare two states:
        init_storage = self.storage
        result_storage = result.storage

        result_event = result_storage['events'][self.id]

        # Not all event parameters need to be tested, some of them can have any
        # value at the moment of creation:
        proper_event = event_params.copy()
        proper_event.update({
            'betsAgainstLiquidityPoolSum': 0,
            'betsForLiquidityPoolSum': 0,
            'isClosed': False,
            'isMeasurementStarted': False,
        })

        selected_event_keys = {
            k: v for k, v in result_event.items() if k in proper_event}
        self.assertDictEqual(proper_event, selected_event_keys)

        self._check_result_integrity(result, self.id)
        return result_storage


    """ Test blocks for startMeasurement/startMeasurementCallback entrypoints: """
    def check_measurement_start_succesfully_runned(self, sender):
        """ Checking that state is correct after start measurement call """

        # Running transaction:
        result = self.contract.startMeasurement(self.id).interpret(
            storage=self.storage, sender=sender, now=self.current_time)

        # Checking that state changed as expected:
        self.assertEqual(len(result.operations), 1)

        operation = result.operations[0]
        self.assertEqual(operation['destination'], self.oracle_address)
        self.assertEqual(operation['parameters']['entrypoint'], 'get')

        currency_pair = operation['parameters']['value']['args'][0]['string']
        self.assertEqual(currency_pair, self.currency_pair)

        event = result.storage['events'][self.id]
        self.assertFalse(event['isMeasurementStarted'])

        self._check_result_integrity(result, self.id)
        return result.storage


    def check_measurement_start_callback_succesfully_executed(
            self, callback_values, source, sender):
        """ Check that emulated callback from oracle is successfull """

        # Pre-transaction storage check:
        self.assertEqual(self.storage['measurementStartCallEventId'], self.id)

        # Running transaction:
        result = self.contract.startMeasurementCallback(callback_values).interpret(
            storage=self.storage, sender=sender,
            now=self.current_time, source=source)

        self.assertEqual(len(result.operations), 1)
        event = result.storage['events'][self.id]

        self.assertEqual(event['startRate'], callback_values['rate'])
        self.assertTrue(event['isMeasurementStarted'])
        self.assertEqual(
            event['measureOracleStartTime'],
            callback_values['lastUpdate'])

        operation = result.operations[0]
        self.assertEqual(operation['destination'], source)
        self.assertAmountEqual(operation, self.measure_start_fee)

        self._check_result_integrity(result, self.id)
        return result.storage


    def check_start_measurement_callback_from_unknown_address_fails(
            self, callback_values, source, sender):
        """ Assert that callback from unknown address
            (not from oracle) is failed """

        result = self.contract.startMeasurement(self.id).interpret(
            storage=self.storage, sender=source, now=self.current_time)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.startMeasurementCallback(callback_values).interpret(
                storage=result.storage, sender=sender, now=RUN_TIME + 12*ONE_HOUR)

        self.assertTrue('Unknown sender' in str(cm.exception))


    def check_wrong_currency_pair_return_from_oracle_fails(
            self, callback_values, source, sender):
        """ Testing that wrong currency_pair returned from oracle
            during measurement is fails """

        result = self.contract.startMeasurement(self.id).interpret(
            storage=self.storage, sender=source, now=self.current_time)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.startMeasurementCallback(callback_values).interpret(
                storage=result.storage, sender=sender, now=self.current_time)

        self.assertTrue("Unexpected currency pair" in str(cm.exception))


    def check_measurement_during_bets_time_failed(
            self, callback_values, source, sender):
        """ Test that startMeasurement call during bets period is falls """

        result = self.contract.startMeasurement(self.id).interpret(
            storage=self.storage, sender=source, now=self.current_time)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.startMeasurementCallback(callback_values).interpret(
                storage=result.storage, sender=sender, now=self.current_time)

        self.assertTrue("Can't start measurement untill betsCloseTime" in str(cm.exception))


    """ Test blocks for close/closeCallback entrypoints: """
    def check_close_succesfully_runned(self, sender):
        """ Check that calling close, succesfully created opearaton
            with call to oracle get """

        result = self.contract.close(self.id).interpret(
            storage=self.storage, sender=sender, now=self.current_time)
        self.assertEqual(len(result.operations), 1)

        operation = result.operations[0]
        self.assertEqual(operation['destination'], self.oracle_address)
        self.assertEqual(operation['parameters']['entrypoint'], 'get')

        currency_pair = operation['parameters']['value']['args'][0]['string']
        self.assertEqual(currency_pair, self.currency_pair)

        self._check_result_integrity(result, self.id)
        return result.storage


    def check_close_callback_succesfully_executed(
            self, callback_values, source, sender):
        """ Check that emulated close callback from oracle is successfull """

        result = self.contract.closeCallback(callback_values).interpret(
            storage=self.storage, sender=self.oracle_address,
            now=self.current_time, source=source)
        self.assertEqual(len(result.operations), 1)

        event = result.storage['events'][self.id]
        self.assertEqual(event['closedRate'], callback_values['rate'])
        self.assertTrue(event['isClosed'])
        self.assertEqual(event['closedOracleTime'], callback_values['lastUpdate'])

        # checking that dynamics is correct:
        dynamics = int(event['closedRate'] / event['startRate']
                       * event['targetDynamicsPrecision'])
        self.assertEqual(event['closedDynamics'], dynamics)

        is_bets_for_win = dynamics > event['targetDynamics']
        self.assertEqual(event['isBetsForWin'], is_bets_for_win)

        operation = result.operations[0]
        self.assertEqual(operation['destination'], source)
        self.assertAmountEqual(operation, self.expiration_fee)

        self._check_result_integrity(result, self.id)
        return result.storage


    def check_closing_before_measurement_fails(
            self, callback_values, source, sender):
        """ Testing that closing before measurement fails """

        result = self.contract.close(self.id).interpret(
            storage=self.storage, sender=source, now=self.current_time)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.closeCallback(callback_values).interpret(
                storage=result.storage, sender=sender, now=self.current_time)

        self.assertTrue("Can't close contract before measurement period started" in str(cm.exception))


    def setUp(self):
        # TODO: decide, should it be here or in tests? If there are always the same
        # setUp, looks like this is good place

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
        self.current_time = RUN_TIME

        # this is eventId that for the tests:
        self.id = 0

        self.default_event_params = {
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
