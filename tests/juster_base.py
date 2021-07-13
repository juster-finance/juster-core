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
from event_model import EventModel
from test_data import generate_storage, ONE_HOUR, ONE_DAY

CONTRACT_FN = '../build/tz/juster.tz'
RUN_TIME = int(time.time())


class JusterBaseTestCase(TestCase):
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
            return {key: value for key, value in dct.items() if value is not None}

        def is_should_be_cleaned(key, value):
            is_dict = type(value) is dict
            is_not_config = key != 'config'
            return is_dict and is_not_config

        return {
            key: clean_dict(value) if is_should_be_cleaned(key, value) else value
            for key, value in storage.items()
        }


    def check_storage_integrity(self, storage):

        def sum_ledger_by_event(ledger, event_id):
            """ Sums all values in ledger for given event_id """

            return sum(
                value if (key[1] == event_id) & (value is not None) else 0
                for key, value in ledger.items())

        bets_above_eq = storage['betsAboveEq']
        bets_below = storage['betsBelow']
        pl_above_eq = storage['providedLiquidityAboveEq']
        pl_below = storage['providedLiquidityBelow']
        deposited_bets = storage['depositedBets']

        for event_id, event in storage['events'].items():
            # Checking that sum of the bets and L is equal to sum in pools.
            # This check should be performed before any withdrawals:
            if event['isClosed']:
                continue

            wins_above_eq_event = sum_ledger_by_event(bets_above_eq, event_id)
            wins_below_event = sum_ledger_by_event(bets_below, event_id)
            liquidity_above_eq_event = sum_ledger_by_event(pl_above_eq, event_id)
            liquidity_below_event = sum_ledger_by_event(pl_below, event_id)
            sum_of_bets = sum_ledger_by_event(deposited_bets, event_id)

            pool_difference = event['poolAboveEq'] - event['poolBelow']
            pool_difference_check = (
                liquidity_above_eq_event - liquidity_below_event
                - wins_below_event + wins_above_eq_event
                # + deposited_bets_below - deposited_bets_above_eq
                # + deposited_bets_above_eq - deposited_bets_below
            )
            self.assertEqual(pool_difference, pool_difference_check)

            self.assertTrue(event['betsCloseTime'] > event['createdTime'])
            self.assertTrue(event['targetDynamics'] > 0)

            if event['measureOracleStartTime'] is not None:
                self.assertTrue(
                    event['measureOracleStartTime'] >= event['betsCloseTime'])

            if event['isClosed']:
                start = event['measureOracleStartTime']
                period = event['measurePeriod']
                self.assertTrue(event['closedOracleTime'] >= start + period)

        self.assertTrue(storage['nextEventId'] > 0)


    def check_provide_liquidity_succeed(
            self, participant, amount, expected_above_eq, expected_below,
            max_slippage=100_000):

        # Running transaction:
        transaction = self.contract.provideLiquidity(
            eventId=self.id,
            expectedRatioBelow=expected_below,
            expectedRatioAboveEq=expected_above_eq,
            maxSlippage=max_slippage
        ).with_amount(amount)

        # Making variables to compare two states:
        result = transaction.interpret(
            storage=self.storage,
            sender=participant,
            now=self.current_time)

        # Checking that state changed as expected for two outcomes:
        for outcome in ['aboveEq', 'below']:
            init_model = EventModel.from_storage(self.storage, self.id, outcome)
            init_model.provide_liquidity(
                participant, amount, expected_above_eq, expected_below)
            result_model = EventModel.from_storage(result.storage, self.id, outcome)
            self.assertEqual(init_model, result_model)

        self.check_storage_integrity(result.storage)
        return result.storage


    def calc_elapsed_time(self):
        event = self.storage['events'][self.id]
        return ((self.current_time - event['createdTime'])
            / (event['betsCloseTime'] - event['createdTime']))


    def check_bet_succeed(
            self, participant, amount, bet, minimal_win):

        # Running transaction:
        transaction = self.contract.bet(
            eventId=self.id, bet=bet, minimalWinAmount=minimal_win).with_amount(amount)

        result = transaction.interpret(
            storage=self.storage, sender=participant, now=self.current_time)

        # Checking that state changed as expected for two outcomes:
        for outcome in ['aboveEq', 'below']:
            init_model = EventModel.from_storage(self.storage, self.id, outcome)
            init_model.bet(participant, amount, bet, self.calc_elapsed_time())
            result_model = EventModel.from_storage(result.storage, self.id, outcome)
            self.assertEqual(init_model, result_model)

        self.check_storage_integrity(result.storage)
        return result.storage


    def _check_withdrawals_sums(
            self, withdraw_amount, result, participant, sender):

        """ Checking that calculated operations are correct """

        # If there are no withdrawal -> there are shouln't be any operations:
        if withdraw_amount == 0:
            self.assertTrue(len(result.operations) == 0)
            return

        # If withdraw amount is positive, there would be 1 or 2 operations:
        # - one if (a) sender === participant
        # - one if (b) time before rewardFeeSplitAfter
        # - one if (c) reward_fee > withdraw_amount
        # - one if (d) it is force majeure
        # - two in all other cases

        event = self.storage['events'][self.id]
        closed_time = event['closedOracleTime']
        reward_fee_split_after = self.storage['config']['rewardFeeSplitAfter']
        reward_fee = self.storage['config']['rewardCallFee']

        if closed_time is None:
            is_time_before_split = False
        else:
            is_time_before_split = self.current_time < closed_time + reward_fee_split_after

        is_sender_equals_participant = participant == sender
        is_force_majeure = event['isForceMajeure']

        if is_time_before_split or is_sender_equals_participant or is_force_majeure:
            self.assertEqual(len(result.operations), 1)
            self.assertAmountEqual(result.operations[0], withdraw_amount)

        else:
            if reward_fee > withdraw_amount:
                self.assertTrue(len(result.operations) == 1)
            else:
                self.assertTrue(len(result.operations) == 2)

            amounts = {
                operation['destination']: int(operation['amount'])
                for operation in result.operations}

            self.assertEqual(sum(amounts.values()), withdraw_amount)
            self.assertTrue(amounts[sender] <= reward_fee)
            participant_amount = max(0, withdraw_amount - reward_fee)
            self.assertEqual(amounts.get(participant, 0), participant_amount)


    def check_withdraw_succeed(self, participant, withdraw_amount, sender=None):

        # If sender is not setted, assuming that participant is the sender:
        sender = sender or participant

        # Running transaction:
        params = {'eventId': self.id, 'participantAddress': participant}
        result = self.contract.withdraw(params).interpret(
            storage=self.storage, sender=sender, now=self.current_time)

        self._check_withdrawals_sums(
            withdraw_amount, result, participant, sender)

        storage = self.remove_none_values(result.storage)
        # Checking that participant removed from all ledgers:
        key = (participant, self.id)
        self.assertFalse(key in storage['betsAboveEq'])
        self.assertFalse(key in storage['betsBelow'])
        self.assertFalse(key in storage['providedLiquidityAboveEq'])
        self.assertFalse(key in storage['providedLiquidityBelow'])
        self.assertFalse(key in storage['liquidityShares'])
        self.assertFalse(key in storage['depositedBets'])

        self.check_storage_integrity(storage)
        return storage


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
            'poolBelow': 0,
            'poolAboveEq': 0,
            'isClosed': False,
            'totalLiquidityShares': 0,
        })

        selected_event_keys = {
            k: v for k, v in result_event.items() if k in proper_event}
        self.assertDictEqual(proper_event, selected_event_keys)

        self.check_storage_integrity(result_storage)
        return result_storage


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
        self.assertTrue(event['measureOracleStartTime'] is None)

        self.check_storage_integrity(result.storage)
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

        init_event = self.storage['events'][self.id]
        event = result.storage['events'][self.id]

        self.assertEqual(event['startRate'], callback_values['rate'])
        self.assertEqual(
            event['measureOracleStartTime'],
            callback_values['lastUpdate'])

        if init_event['measureStartFee'] == 0:
            self.assertEqual(len(result.operations), 0)

        if init_event['measureStartFee'] > 0:
            self.assertEqual(len(result.operations), 1)

            operation = result.operations[0]
            self.assertEqual(operation['destination'], source)
            self.assertAmountEqual(operation, self.measure_start_fee)

        self.check_storage_integrity(result.storage)
        return result.storage


    def check_start_measurement_callback_fails_with(
            self, callback_values, source, sender, msg_contains=''):
        """ Making a call to startMeasurement and returned callback
            to startMeasurementCallback with provided params.
            Checks that there was MichelsonRuntimeError
            If msg_contains is provided: checking that this msg_contains
            is inside string form of cathced exception
        """

        with self.assertRaises(MichelsonRuntimeError) as cm:
            result = self.contract.startMeasurement(self.id).interpret(
                storage=self.storage, sender=source, now=self.current_time)

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

        self.check_storage_integrity(result.storage)
        return result.storage


    def check_close_callback_succeed(
            self, callback_values, source, sender):
        """ Check that emulated close callback from oracle is successfull """

        result = self.contract.closeCallback(callback_values).interpret(
            storage=self.storage, sender=self.oracle_address,
            now=self.current_time, source=source)

        init_event = self.storage['events'][self.id]
        event = result.storage['events'][self.id]

        self.assertEqual(event['closedRate'], callback_values['rate'])
        self.assertTrue(event['isClosed'])
        self.assertEqual(event['closedOracleTime'], callback_values['lastUpdate'])

        # checking that dynamics is correct:
        dynamics = int(event['closedRate'] / event['startRate']
                       * self.storage['targetDynamicsPrecision'])
        self.assertEqual(event['closedDynamics'], dynamics)

        is_bets_above_eq_win = dynamics >= event['targetDynamics']
        self.assertEqual(event['isBetsAboveEqWin'], is_bets_above_eq_win)

        if init_event['expirationFee'] == 0:
            self.assertEqual(len(result.operations), 0)

        if init_event['expirationFee'] > 0:
            self.assertEqual(len(result.operations), 1)
            operation = result.operations[0]
            self.assertEqual(operation['destination'], source)
            self.assertAmountEqual(operation, self.expiration_fee)

        self.check_storage_integrity(result.storage)
        return result.storage


    def check_close_callback_fails_with(
            self, callback_values, source, sender, msg_contains=''):
        """ Checking that closing fails with message msg_contains """

        with self.assertRaises(MichelsonRuntimeError) as cm:
            result = self.contract.close(self.id).interpret(
                storage=self.storage, sender=source, now=self.current_time)

            res = self.contract.closeCallback(callback_values).interpret(
                storage=result.storage, sender=sender, now=self.current_time)

        self.assertTrue(msg_contains in str(cm.exception))


    def check_update_config_succeed(self, lambda_code, sender):
        """ Checking that updateConfig call is succeed """

        result = self.contract.updateConfig(lambda_code).interpret(
            storage=self.storage, sender=sender, now=self.current_time)

        return result.storage


    def check_update_config_fails_with(self, lambda_code, sender, msg_contains=''):
        """ Checking that updateConfig fails with error msg_contains """

        with self.assertRaises(MichelsonRuntimeError) as cm:
            result = self.contract.updateConfig(lambda_code).interpret(
                storage=self.storage, sender=sender, now=self.current_time)

        self.assertTrue(msg_contains in str(cm.exception))


    def check_trigger_force_majeure_succeed(self, sender):

        event = self.storage['events'][self.id]
        was_closed = event['isClosed']
        result = self.contract.triggerForceMajeure(self.id).interpret(
            storage=self.storage, sender=sender, now=self.current_time)

        # There are should be no operation if event is closed and
        # one opertion if event is not closed with fees

        if was_closed:
            self.assertEqual(len(result.operations), 0)
        else:
            self.assertEqual(len(result.operations), 1)
            operation = result.operations[0]

            # calculating fees: it should be expirationFee + meas. start fee:
            amount = event['expirationFee']
            if event['measureOracleStartTime'] is None:
                amount += event['measureStartFee']

            self.assertAmountEqual(operation, amount)

        return result.storage


    def check_trigger_force_majeure_fails_with(self, sender, msg_contains=''):

        with self.assertRaises(MichelsonRuntimeError) as cm:
            result = self.contract.triggerForceMajeure(self.id).interpret(
                storage=self.storage, sender=sender, now=self.current_time)

        self.assertTrue(msg_contains in str(cm.exception))


    def check_claim_baking_rewards_succeed(self, expected_reward, sender):

        result = self.contract.claimBakingRewards().interpret(
            now=self.current_time,
            storage=self.storage,
            sender=sender)
        self.assertEqual(len(result.operations), 1)

        operation = result.operations[0]
        self.assertEqual(operation['destination'], self.manager)
        self.assertAmountEqual(operation, expected_reward)

        return result.storage


    def check_claim_baking_rewards_fails_with(
        self, expected_reward, sender, msg_contains=''):

        with self.assertRaises(MichelsonRuntimeError) as cm:
            result = self.contract.claimBakingRewards().interpret(
                now=self.current_time,
                storage=self.storage,
                sender=sender)

        self.assertTrue(msg_contains in str(cm.exception))


    def check_claim_retained_profits_succeed(self, expected_profit, sender):

        result = self.contract.claimRetainedProfits().interpret(
            now=self.current_time,
            storage=self.storage,
            sender=sender)
        self.assertEqual(len(result.operations), 1)

        operation = result.operations[0]
        self.assertEqual(operation['destination'], self.manager)
        self.assertAmountEqual(operation, expected_profit)

        return result.storage


    def check_claim_retained_profits_fails_with(
        self, expected_profit, sender, msg_contains=''):

        with self.assertRaises(MichelsonRuntimeError) as cm:
            result = self.contract.claimRetainedProfits().interpret(
                now=self.current_time,
                storage=self.storage,
                sender=sender)

        self.assertTrue(msg_contains in str(cm.exception))


    def setUp(self):

        self.contract = ContractInterface.from_file(join(dirname(__file__), CONTRACT_FN))

        # four participants and their pk hashes:
        self.a = 'tz1iQE8ijR5xVPffBUPFubwB9XQJuyD9qsoJ'
        self.b = 'tz1MdaJfWzP5pPx3gwPxfdLZTHW6js9havos'
        self.c = 'tz1RS9GoEXakf9iyBmSaheLMcakFRtzBXpWE'
        self.d = 'tz1TdKuFwYgbPHHb7y1VvLH4xiwtAzcjwDjM'

        self.manager = self.a

        self.oracle_address = 'KT1SUP27JhX24Kvr11oUdWswk7FnCW78ZyUn'
                # florencenet: KT1SUP27JhX24Kvr11oUdWswk7FnCW78ZyUn
                # edo2net:     KT1RCNpUEDjZAYhabjzgz1ZfxQijCDVMEaTZ
        self.currency_pair = 'XTZ-USD'
        self.current_time = RUN_TIME

        # this is eventId that for the tests:
        self.id = 0

        self.default_event_params = {
            'currencyPair': self.currency_pair,
            'targetDynamics': 1_000_000,
            'betsCloseTime': RUN_TIME + 24*ONE_HOUR,
            'measurePeriod': 12*ONE_HOUR,
            'liquidityPercent': 0,
        }

        self.init_storage = generate_storage(self.manager, self.oracle_address)
        self.default_config = self.init_storage['config']
        self.measure_start_fee = self.init_storage['config']['measureStartFee']
        self.expiration_fee = self.init_storage['config']['expirationFee']

        # this self.storage will be used in all blocks:
        self.storage = self.init_storage.copy()
