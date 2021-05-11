""" This is base class that used in different tests.
    It uses pytezos intepret method and provides calls to all entrypoints that tested.

    For each entrypoint call there are two methods:
        - one for successful call that checks is state changed correctly
            name: f'check_{entrypoint_call}_succeed'
        - one for failwith call that checks that MichelsonRuntimeError is raised with some message
            name: f'check_{entrypoint_call}_fails_with'

    The one who checks for error have the same interface but with msg_contains param provided.

    After each contract call, new state returned.

    TODO: try to move all this interactions inside sandbox?
"""

from unittest import TestCase
import time
from os.path import dirname, join
from pytezos import ContractInterface, pytezos, MichelsonRuntimeError


CONTRACT_FN = 'baking_bet.tz'
RUN_TIME = int(time.time())
ONE_HOUR = 60*60


""" Some smart contract logic reimplemented here: """

def calculate_liquidity_bonus_multiplier(event, current_time):
    """ Returns multiplier that reduces provided LP bonus lineary
        over betting time """

    close_time = event['betsCloseTime']
    start_time = event['createdTime']
    return (close_time - current_time) / (close_time - start_time)


def calculate_bet_return(top, bottom, amount):
    """ Calculates the amount that would be returned if participant wins
        Not included the bet amount itself, only added value
    """

    ratio = top / (bottom + amount)
    return int(amount * ratio)


def calculate_bet_params_change(storage, event_id, participant, bet, amount):
    """ Returns dict with differences that caused
        by adding new bet to event
    """

    event = storage['events'][event_id]
    key = (participant, event_id)

    if bet == 'for':
        top = event['poolAgainst']
        bottom = event['poolFor']
        for_count = 0 if key in storage['betsFor'] else 1

        return dict(
            diff_for=amount,
            diff_against=-calculate_bet_return(top, bottom, amount),
            for_count=for_count,
            against_count=0
        )

    elif bet == 'against':
        top = event['poolFor']
        bottom = event['poolAgainst']
        against_count = 0 if key in storage['betsAgainst'] else 1

        return dict(
            diff_for=-calculate_bet_return(top, bottom, amount),
            diff_against=amount,
            for_count=0,
            against_count=against_count
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
        provided_liquidity_sum_ledger = sum_by_id(res.storage['providedLiquidity'], event_id)
        total_ledger_sums = (
            bets_for_sum_ledger + bets_against_sum_ledger + provided_liquidity_sum_ledger)

        bets_for_sum_event = res.storage['events'][event_id]['poolFor']
        bets_against_sum_event = res.storage['events'][event_id]['poolAgainst']
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


    def check_provide_liquidity_succeed(
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
        total_liquidity = (init_event['poolFor']
                           + init_event['poolAgainst'])

        if total_liquidity > 0:
            added_for_share = (
                init_event['poolFor'] / total_liquidity)
            added_against_share = (
                init_event['poolAgainst'] / total_liquidity)

        else:
            # scenario with first LP:
            added_for_share = (
                expected_for / (expected_for + expected_against))
            added_against_share = (
                expected_against / (expected_for + expected_against))

        added_for = int(amount * added_for_share)
        added_against = int(amount * added_against_share)

        difference_for = (result_event['poolFor']
                          - init_event['poolFor'])
        difference_against = (result_event['poolAgainst']
                              - init_event['poolAgainst'])

        self.assertEqual(difference_for, added_for)
        self.assertEqual(difference_against, added_against)

        self.assertEqual(
            len(result_storage['betsFor']),
            len(init_storage['betsFor']))

        self.assertEqual(
            len(result_storage['betsAgainst']),
            len(init_storage['betsAgainst']))

        # If participant added liquidity before, it should not change
        # ledger records count. If it is not - records should be incresed by 1

        is_already_lp = (participant, self.id) in init_storage['providedLiquidity']
        added_count = 0 if is_already_lp else 1

        self.assertEqual(
            len(result_storage['providedLiquidity']),
            len(init_storage['providedLiquidity']) + added_count)

        self.assertEqual(len(
            result_storage['liquidityForShares']),
            len(init_storage['liquidityForShares']) + added_count)

        self.assertEqual(
            len(result_storage['liquidityAgainstShares']),
            len(init_storage['liquidityAgainstShares']) + added_count)

        m = calculate_liquidity_bonus_multiplier(init_event, self.current_time)
        self.assertEqual(
            result_event['totalLiquidityForShares'],
            init_event['totalLiquidityForShares'] + int(m*added_for))

        self.assertEqual(
            result_event['totalLiquidityAgainstShares'],
            init_event['totalLiquidityAgainstShares'] + int(m*added_against))

        self._check_result_integrity(result, self.id)
        return result_storage


    def check_provide_liquidity_fails_with(
        self, participant, amount, expected_for, expected_against,
        max_slippage=100_000, msg_contains=''):

        raise Exception('Not implemented yet')


    def check_bet_succeed(
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
        bet_result = calculate_bet_params_change(
            init_storage, self.id, participant, bet, amount)

        self.assertEqual(
            result_event['poolFor'],
            init_event['poolFor'] + bet_result['diff_for'])

        self.assertEqual(
            result_event['poolAgainst'],
            init_event['poolAgainst'] + bet_result['diff_against'])

        self.assertEqual(
            len(result_storage['betsFor']),
            len(init_storage['betsFor']) + bet_result['for_count'])

        self.assertEqual(
            len(result_storage['betsAgainst']),
            len(init_storage['betsAgainst']) + bet_result['against_count'])

        # TODO: check sum in participant ledgers (include liquidity fee)
        # TODO: check forProfit / againstProfit

        self._check_result_integrity(result, self.id)
        return result_storage


    def check_bet_fails_with(
            self, participant, amount, bet, minimal_win, msg_contains=''):
        """ Makes a call to bet entrypoint and checks that there was MichelsonRuntimeError
            If msg_contains is provided: checking that this msg_contains
            is inside string form of cathced exception
        """

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

        self.assertTrue(msg_contains in str(cm.exception))


    def check_withdraw_succeed(self, participant, withdraw_amount):

        # Running transaction:
        result = self.contract.withdraw(self.id).interpret(
            storage=self.storage, sender=participant, now=self.current_time)

        # If there are no withdrawal -> there are shouln't be any operations:
        if withdraw_amount == 0:
            self.assertTrue(len(result.operations) == 0)
        else:
            # Checking that withdrawals amount equal to expected:
            self.assertAmountEqual(result.operations[0], withdraw_amount)

        # TODO: check participant removed from ledgers? (maybe separate method)

        self._check_result_integrity(result, self.id)
        return self.remove_none_values(result.storage)


    def check_withdraw_fails_with(self, participant, withdraw_amount, msg_contains=''):

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.withdraw(self.id).interpret(
                storage=self.storage, sender=participant, now=self.current_time)

        self.assertTrue(msg_contains in str(cm.exception))


    def check_new_event_succeed(self, event_params, amount):
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
            'poolAgainst': 0,
            'poolFor': 0,
            'isClosed': False,
            'isMeasurementStarted': False,
            'forProfit': 0,
            'againstProfit': 0,
            'totalLiquidityForShares': 0,
            'totalLiquidityAgainstShares': 0
        })

        selected_event_keys = {
            k: v for k, v in result_event.items() if k in proper_event}
        self.assertDictEqual(proper_event, selected_event_keys)

        self._check_result_integrity(result, self.id)
        return result_storage


    def check_new_event_fails_with(
        self, event_params, amount, msg_contains=''):

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.newEvent(event_params).interpret(
                storage=self.storage, now=self.current_time)

        self.assertTrue(msg_contains in str(cm.exception))


    def check_start_measurement_succeed(self, sender):
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


    def check_start_measurement_callback_succeed(
            self, callback_values, source, sender):
        """ Check that emulated callback from oracle is successfull """

        # Pre-transaction storage check:    
        self.assertEqual(self.storage['measurementStartCallId'], self.id)

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


    def check_start_measurement_callback_fails_with(
            self, callback_values, source, sender, msg_contains=''):
        """ Making a call to startMeasurement and returned callback
            to startMeasurementCallback with provided params.
            Checks that there was MichelsonRuntimeError
            If msg_contains is provided: checking that this msg_contains
            is inside string form of cathced exception
        """

        result = self.contract.startMeasurement(self.id).interpret(
            storage=self.storage, sender=source, now=self.current_time)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.startMeasurementCallback(callback_values).interpret(
                storage=result.storage, sender=sender, now=self.current_time)

        self.assertTrue(msg_contains in str(cm.exception))


    def check_close_succeed(self, sender):
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


    def check_close_callback_succeed(
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


    def check_close_callback_fails_with(
            self, callback_values, source, sender, msg_contains=''):
        """ Testing that closing before measurement fails """

        result = self.contract.close(self.id).interpret(
            storage=self.storage, sender=source, now=self.current_time)

        with self.assertRaises(MichelsonRuntimeError) as cm:
            res = self.contract.closeCallback(callback_values).interpret(
                storage=result.storage, sender=sender, now=self.current_time)

        self.assertTrue(msg_contains in str(cm.exception))


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
        # florencenet: KT1SUP27JhX24Kvr11oUdWswk7FnCW78ZyUn
        # edo2net:     KT1RCNpUEDjZAYhabjzgz1ZfxQijCDVMEaTZ

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
            'betsFor': {},
            'betsAgainst': {},
            'providedLiquidity': {},
            'liquidityForShares': {},
            'liquidityAgainstShares': {},
            'forProfitDiff': {},
            'againstProfitDiff': {},
            'depositedBets': {},
            'lastEventId': 0,
            'closeCallId': None,
            'measurementStartCallId': None
        }

        # this self.storage will be used in all blocks:
        self.storage = self.init_storage.copy()
