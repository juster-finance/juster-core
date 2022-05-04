from unittest import TestCase
import time
import math
from decimal import Decimal
from os.path import dirname, join
from pytezos import ContractInterface, pytezos, MichelsonRuntimeError
from tests.test_data import (
    ONE_HOUR,
    ONE_DAY,
    generate_pool_storage,
    generate_line_params,
    generate_juster_config
)

POOL_FN = '../../../build/contracts/pool.tz'
RUN_TIME = int(time.time())


class PoolBaseTestCase(TestCase):
    """ Methods used to check different state transformations for Pool
        Each check method runs one transaction and then compare storage
        before and after transaction execution. At the end each check
        method returns new storage
    """

    def setUp(self):
        self.pool = ContractInterface.from_file(
            join(dirname(__file__), POOL_FN))

        # four participants and their pk hashes:
        self.a = 'tz1iQE8ijR5xVPffBUPFubwB9XQJuyD9qsoJ'
        self.b = 'tz1MdaJfWzP5pPx3gwPxfdLZTHW6js9havos'
        self.c = 'tz1RS9GoEXakf9iyBmSaheLMcakFRtzBXpWE'
        self.d = 'tz1TdKuFwYgbPHHb7y1VvLH4xiwtAzcjwDjM'

        self.manager = self.a
        self.address = 'contract'

        self.juster_address = 'KT1SUP27JhX24Kvr11oUdWswk7FnCW78ZyUn'
        self.current_time = RUN_TIME

        self.init_storage = generate_pool_storage(manager=self.manager)

        self.drop_changes()


    def drop_changes(self):
        self.storage = self.init_storage.copy()
        self.balances = {self.address: 0}
        self.next_event_id = 0


    def update_balance(self, address, amount):
        """ Used to track balances of different users """
        self.balances[address] = self.balances.get(address, 0) + amount
        self.assertTrue(self.balances['contract'] >= 0)


    def get_next_liquidity(self):
        """ Returns next event liquidity value in int """
        return int(self.storage['nextLiquidityF'] / self.storage['precision'])

    def add_line(
            self,
            sender=None,
            currency_pair='XTZ-USD',
            max_events=2,
            bets_period=3600,
            last_bets_close_time=0,
            amount=0,
            juster_address=None,
            min_betting_period=0,
            advance_time=0,
            measure_period=3600
        ):

        sender = sender or self.manager
        juster_address = juster_address or self.juster_address

        line_params = generate_line_params(
            currency_pair=currency_pair,
            max_events=max_events,
            bets_period=bets_period,
            last_bets_close_time=last_bets_close_time,
            juster_address=juster_address,
            min_betting_period=min_betting_period,
            advance_time=advance_time,
            measure_period=measure_period
        )

        call = self.pool.addLine(line_params)
        result = call.with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender
        )

        line_id = self.storage['nextLineId']
        self.assertEqual(
            line_id + 1,
            result.storage['nextLineId']
        )

        added_line = result.storage['lines'][self.storage['nextLineId']]
        self.assertEqual(added_line['currencyPair'], currency_pair)
        self.assertEqual(added_line['maxEvents'], max_events)
        self.assertEqual(added_line['betsPeriod'], bets_period)
        self.assertEqual(added_line['lastBetsCloseTime'], last_bets_close_time)

        self.storage = result.storage
        return line_id


    def deposit_liquidity(self, sender=None, amount=1_000_000):
        sender = sender or self.manager
        call = self.pool.depositLiquidity()
        result = call.with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            balance=self.balances[self.address] + amount
        )

        entry_id = self.storage['nextEntryId']
        self.assertEqual(
            entry_id + 1,
            result.storage['nextEntryId']
        )

        added_position = result.storage['entries'][entry_id]
        expected_unlock_time = self.storage['entryLockPeriod'] + self.current_time
        self.assertEqual(added_position['acceptAfter'], expected_unlock_time)
        self.assertEqual(added_position['amount'], amount)
        self.assertEqual(added_position['provider'], sender)

        entry_liquidity_diff = (
            result.storage['entryLiquidityF']
            - self.storage['entryLiquidityF']
        )
        amount_f = self.storage['precision'] * amount
        self.assertEqual(entry_liquidity_diff, amount_f)

        self.storage = result.storage
        self.update_balance(self.address, amount)
        self.update_balance(sender, -amount)

        return entry_id


    def _calc_free_liquidity(self):
        return (
            self.balances['contract'] * self.storage['precision']
            - self.storage['withdrawableLiquidityF']
            - self.storage['entryLiquidityF']
        )


    def _calc_total_liquidity(self):
        return self._calc_free_liquidity() + self.storage['activeLiquidityF']


    def approve_liquidity(self, sender=None, entry_id=0, amount=0):
        sender = sender or self.manager
        call = self.pool.approveLiquidity(entry_id)
        result = call.with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            balance=self.balances[self.address]
        )

        self.assertTrue(result.storage['entries'][entry_id] is None)
        result.storage['entries'].pop(entry_id)

        position_id = self.storage['nextPositionId']
        added_position = result.storage['positions'][position_id]
        self.assertEqual(added_position['addedCounter'], self.storage['counter'])
        self.assertEqual(result.storage['counter'], self.storage['counter'] + 1)

        entry = self.storage['entries'][entry_id]
        self.assertEqual(added_position['provider'], entry['provider'])

        amount = entry['amount']
        amount_f = amount * self.storage['precision']
        total_shares = self.storage['totalShares']
        total_liquidity_f = self._calc_total_liquidity()

        is_new = total_shares == 0
        # TODO: replace calculations with decimals:
        expected_added_shares = int(
            amount if is_new else amount_f * total_shares / total_liquidity_f)

        self.assertEqual(added_position['shares'], expected_added_shares)
        entry_liquidity_diff_f = (
            self.storage['entryLiquidityF']
            - result.storage['entryLiquidityF']
        )
        self.assertEqual(entry_liquidity_diff_f, amount_f)

        self.storage = result.storage
        return position_id


    def cancel_liquidity(self, sender=None, entry_id=0, amount=0):
        sender = sender or self.manager
        call = self.pool.cancelLiquidity(entry_id)
        result = call.with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            balance=self.balances[self.address]
        )

        position = self.storage['entries'][entry_id]
        self.assertEqual(position['provider'], sender)
        liquidity_diff_f = (
            self.storage['entryLiquidityF'] - result.storage['entryLiquidityF'])
        amount_f = position['amount'] * self.storage['precision']
        self.assertEqual(liquidity_diff_f, amount_f)

        self.assertTrue(result.storage['entries'][entry_id] is None)
        result.storage['entries'].pop(entry_id)

        entry = self.storage['entries'][entry_id]
        self.assertEqual(len(result.operations), 1)
        op = result.operations[0]
        self.assertEqual(op['destination'], sender)
        self.assertEqual(op['amount'], str(entry['amount']))

        self.storage = result.storage


    def _check_withdrawal_creation(self, result, position_id, shares):
        next_id = self.storage['nextWithdrawalId']
        self.assertEqual(result.storage['nextWithdrawalId'], next_id+1)
        actual_withdrawal = result.storage['withdrawals'][next_id]
        position = self.storage['positions'][position_id]

        liquidity_units = (
            self.storage['liquidityUnits'] - position['entryLiquidityUnits'])

        expected_withdrawal = {
            'liquidityUnits': liquidity_units,
            'positionId': position_id,
            'shares': shares
        }

        self.assertDictEqual(expected_withdrawal, actual_withdrawal)


    def _check_position_diff(self, result, position_id, shares):
        old_position = self.storage['positions'][position_id]
        new_position = result.storage['positions'][position_id]

        self.assertEqual(old_position['provider'], new_position['provider'])
        self.assertEqual(old_position['provider'], new_position['provider'])

        shares_diff = old_position['shares'] - new_position['shares']
        self.assertEqual(shares_diff, shares)

        self.assertEqual(
            new_position['addedCounter'], old_position['addedCounter'])
        total_shares_diff = (
            self.storage['totalShares'] - result.storage['totalShares'])
        self.assertEqual(total_shares_diff, shares)


    def _calc_and_check_claim_excpected_amount(self, result, position_id, shares):
        position = self.storage['positions'][position_id]
        precision = Decimal(self.storage['precision'])
        provided_liquidity_sum_f = Decimal(0)
        shares = Decimal(shares)
        impacted_count = 0

        for event_id in self.storage['activeEvents']:
            event = self.storage['events'][event_id]
            is_impacted = position['addedCounter'] < event['createdCounter']
            have_shares = shares > 0

            if is_impacted and have_shares:
                key = (event_id, position_id)
                default_claim = {'shares': 0}
                old_claim = self.storage['claims'].get(key, default_claim)
                new_claim = result.storage['claims'][key]

                shares_diff = new_claim['shares'] - old_claim['shares']
                self.assertEqual(shares_diff, shares)

                provided = Decimal(event['provided'])
                total_shares = Decimal(event['totalShares'])
                provided_f = int(provided * shares * precision / total_shares)
                provided_liquidity_sum_f += provided_f

                impacted_count += 1

        active_liquidity_diff_f = (
            self.storage['activeLiquidityF']
            - result.storage['activeLiquidityF']
        )

        self.assertEqual(active_liquidity_diff_f, provided_liquidity_sum_f)

        # TODO: make all tests internal calculations in Decimals
        total_liquidity_f = self._calc_total_liquidity()
        user_liquidity_f = total_liquidity_f * shares / self.storage['totalShares']

        provided_estimate_f = (
            user_liquidity_f * impacted_count
            / self.storage['maxEvents'])

        expected_amount_f = int(user_liquidity_f) - int(provided_estimate_f)
        expected_amount = int(expected_amount_f / precision)

        return expected_amount


    def _check_claim_amount(self, result, expected_amount):
        if expected_amount:
            self.assertTrue(len(result.operations) == 1)
            op = result.operations[0]
            amount = int(op['amount'])
            self.assertEqual(expected_amount, amount)


    def claim_liquidity(self, sender=None, position_id=0, shares=1_000_000, amount=0):
        sender = sender or self.manager
        params = {
            'positionId': position_id,
            'shares': shares
        }

        call = self.pool.claimLiquidity(params)
        result = call.with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            balance=self.balances[self.address]
        )

        self._check_position_diff(result, position_id, shares)
        self._check_withdrawal_creation(result, position_id, shares)
        expected_amount = self._calc_and_check_claim_excpected_amount(
            result, position_id, shares)
        self._check_claim_amount(result, expected_amount)

        self.storage = result.storage

        self.update_balance(self.address, -expected_amount)
        self.update_balance(sender, expected_amount)
        return expected_amount


    def withdraw_liquidity(self, sender=None, positions=None, amount=0):
        sender = sender or self.manager
        default_positions = [dict(positionId=0, eventId=0)]
        positions = default_positions if positions is None else positions

        call = self.pool.withdrawLiquidity(positions)
        result = call.with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            balance=self.balances[self.address]
        )

        precision = Decimal(self.storage['precision'])
        amounts_f = {}
        for position in positions:
            key = (position['eventId'], position['positionId'])
            self.assertTrue(result.storage['claims'][key] is None)
            result.storage['claims'].pop(key)

            claim = self.storage['claims'][key]
            event = self.storage['events'][position['eventId']]
            event_result_f = Decimal(event['result']) * precision
            shares = Decimal(claim['shares'])
            total_shares = Decimal(event['totalShares'])
            amount_f = int(shares * event_result_f / total_shares )
            provider = claim['provider']

            if amount_f > 0:
                amounts_f[provider] = amounts_f.get(provider, 0) + amount_f

        amounts_sum_f = sum(amounts_f.values())
        self.assertEqual(len(amounts_f), len(result.operations))

        withdrawable_diff_f = (
            Decimal(self.storage['withdrawableLiquidityF'])
            - Decimal(result.storage['withdrawableLiquidityF'])
        )
        self.assertEqual(withdrawable_diff_f, amounts_sum_f)
        self.storage = result.storage

        amounts = {
            key: int(amount / precision)
            for key, amount in amounts_f.items()
        }

        if amounts_sum_f:
            for op in result.operations:
                amount = int(op['amount'])
                participant = op['destination']
                self.assertEqual(amount, amounts[participant])

                self.update_balance(self.address, -amount)
                self.update_balance(participant, amount)

        return amounts


    def pay_reward(self, sender=None, event_id=0, amount=1_000_000):
        sender = sender or self.juster_address

        call = self.pool.payReward(event_id)
        result = call.with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            balance=self.balances[self.address]
        )

        self.assertEqual(result.storage['events'][event_id]['result'], amount)
        self.assertFalse(event_id in result.storage['activeEvents'])
        withdrawable_diff_f = (
            Decimal(result.storage['withdrawableLiquidityF'])
            - Decimal(self.storage['withdrawableLiquidityF'])
        )

        event = self.storage['events'][event_id]
        amount_f = Decimal(amount * self.storage['precision'])
        locked_shares = Decimal(event['lockedShares'])
        total_shares = Decimal(event['totalShares'])
        event_lock_f = int(locked_shares * amount_f / total_shares)
        self.assertEqual(withdrawable_diff_f, event_lock_f)

        self.storage = result.storage
        self.update_balance(sender, -amount)
        self.update_balance(self.address, amount)


    def _check_liquidity_units_calc(self, result, event_line_id, amount):
        line = result.storage['lines'][event_line_id]
        liquidity_units_diff = (
            result.storage['liquidityUnits']
            - self.storage['liquidityUnits'])

        duration = (
            line['measurePeriod']
            + line['lastBetsCloseTime']
            - self.current_time)

        expected_liquidity_units = int(
            duration
            * amount
            / self.storage['totalShares']
        )

        self.assertEqual(liquidity_units_diff, expected_liquidity_units)


    def _check_create_event_active_liquidity_calc(self, result, amount_f):
        active_liquidity_diff_f = (
            result.storage['activeLiquidityF']
            - self.storage['activeLiquidityF']
        )

        self.assertEqual(active_liquidity_diff_f, amount_f)


    def _check_added_event(self, result, next_event_id, amount):
        added_event = result.storage['events'][next_event_id]

        target_event = {
            'createdCounter': self.storage['counter'],
            'lockedShares': 0,
            'provided': amount,
            'result': None,
            'totalShares': self.storage['totalShares']
        }

        self.assertDictEqual(added_event, target_event)


    def create_event(
            self,
            sender=None,
            event_line_id=0,
            next_event_id=None,
            amount=0,
            config=None):

        sender = sender or self.manager
        next_event_id = next_event_id or self.next_event_id
        config = config or generate_juster_config(
            expiration_fee=0, measure_start_fee=0)

        contract_call = self.pool.createEvent(event_line_id)
        juster_address = self.storage['lines'][event_line_id]['juster']
        result = contract_call.with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            view_results={
                f'{juster_address}%getNextEventId': next_event_id,
                f'{juster_address}%getConfig': config
            },
            balance=self.balances[self.address]
        )

        event_fee = int(result.operations[0]['amount'])
        provide_op = int(result.operations[1]['amount'])
        precision = self.storage['precision']
        provided_amount = event_fee + provide_op
        provided_amount_f = provided_amount * precision

        self.assertTrue(next_event_id in result.storage['activeEvents'])
        self._check_create_event_active_liquidity_calc(result, provided_amount_f)
        self._check_added_event(result, next_event_id, provided_amount)
        self.assertEqual(self.storage['counter'] + 1, result.storage['counter'])
        self._check_liquidity_units_calc(
            result, event_line_id=event_line_id, amount=provided_amount)

        self.assertEqual(len(result.operations), 2)

        new_event_fee = config['expirationFee'] + config['measureStartFee']
        self.assertEqual(event_fee, new_event_fee)
        expected_provided_f = min(
            self.storage['nextLiquidityF'], self._calc_free_liquidity())
        expected_provided = int(expected_provided_f / precision)
        self.assertEqual(provided_amount, expected_provided)
        self.assertEqual(result.operations[0]['destination'], juster_address)
        self.assertEqual(result.operations[1]['destination'], juster_address)

        self.storage = result.storage
        self.update_balance(self.address, -provided_amount)
        self.update_balance(juster_address, provided_amount)
        self.next_event_id += 1
        return next_event_id


    def trigger_pause_line(self, sender=None, line_id=0, amount=0):
        sender = sender or self.manager

        contract_call = self.pool.triggerPauseLine(line_id)
        result = contract_call.with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            balance=self.balances[self.address]
        )

        init_state = self.storage['lines'][line_id]['isPaused']
        result_state = result.storage['lines'][line_id]['isPaused']
        self.assertEqual(init_state, not result_state)

        active_events_diff = (
            result.storage['maxEvents']
            - self.storage['maxEvents']
        )

        self.assertEqual(
            abs(active_events_diff),
            self.storage['lines'][line_id]['maxEvents'])

        next_event_liquidity_diff = (
            result.storage['nextLiquidityF']
            - self.storage['nextLiquidityF']
        )

        calculated_diff = (
            self.storage['nextLiquidityF']
            * self.storage['maxEvents']
            / result.storage['maxEvents']
        ) - self.storage['nextLiquidityF']

        self.assertEqual(
            int(next_event_liquidity_diff / self.storage['precision']),
            int(calculated_diff / self.storage['precision'])
        )

        self.storage = result.storage
        return result_state


    def trigger_pause_deposit(self, sender=None, amount=0):
        sender = sender or self.manager

        contract_call = self.pool.triggerPauseDeposit()
        result = contract_call.with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            balance=self.balances[self.address]
        )

        init_state = self.storage['isDepositPaused']
        result_state = result.storage['isDepositPaused']
        self.assertEqual(init_state, not result_state)

        self.storage = result.storage

        return result_state


    def set_entry_lock_period(self, sender=None, amount=0, new_period=0):
        sender = sender or self.manager

        contract_call = self.pool.setEntryLockPeriod(new_period)
        result = contract_call.with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            balance=self.balances[self.address]
        )

        self.assertEqual(result.storage['entryLockPeriod'], new_period)

        self.storage = result.storage


    def propose_manager(self, sender=None, proposed_manager=None, amount=0):
        sender = sender or self.manager
        proposed_manager = proposed_manager or self.manager

        call = self.pool.proposeManager(proposed_manager).with_amount(amount)
        result = call.interpret(
            now=self.current_time,
            storage=self.storage,
            sender=sender)
        self.assertEqual(len(result.operations), 0)
        self.assertEqual(result.storage['proposedManager'], proposed_manager)

        self.storage = result.storage


    def accept_ownership(self, sender=None, amount=0):
        sender = sender or self.manager

        call = self.pool.acceptOwnership().with_amount(amount)
        result = call.interpret(
            now=self.current_time,
            storage=self.storage,
            sender=sender)
        self.assertEqual(len(result.operations), 0)
        self.assertEqual(result.storage['manager'], sender)

        self.storage = result.storage


    def set_delegate(self, sender=None, new_delegate=None, amount=0):
        sender = sender or self.manager
        new_delegate = new_delegate or self.c

        call = self.pool.setDelegate(new_delegate).with_amount(amount)
        result = call.interpret(
            now=self.current_time,
            storage=self.storage,
            sender=sender)
        self.assertEqual(len(result.operations), 1)
        op = result.operations[0]

        self.assertEqual(op['kind'], 'delegation')
        self.assertEqual(op['delegate'], new_delegate)


    def default(self, sender=None, amount=0):
        sender = sender or self.manager

        call = self.pool.default().with_amount(amount)
        result = call.interpret(
            now=self.current_time,
            storage=self.storage,
            sender=sender)
        self.assertEqual(len(result.operations), 0)
        liquidity_diff = int(
            (result.storage['nextLiquidityF'] - self.storage['nextLiquidityF'])
            / self.storage['precision'])

        calc_diff = amount / self.storage['maxEvents']
        self.assertTrue(abs(liquidity_diff - calc_diff) <= 1)
        self.storage = result.storage

        self.balances[sender] = self.balances.get(sender, 0) - amount
        self.balances['contract'] = self.balances.get('contract', 0) + amount


    def get_line(self, line_id):
        return self.pool.getLine(line_id).onchain_view(storage=self.storage)


    def get_next_line_id(self):
        return self.pool.getNextLineId().onchain_view(storage=self.storage)


    def get_entry(self, entry_id):
        return self.pool.getEntry(entry_id).onchain_view(storage=self.storage)


    def get_next_entry_id(self):
        return self.pool.getNextEntryId().onchain_view(storage=self.storage)


    def get_position(self, position_id):
        return self.pool.getPosition(position_id).onchain_view(storage=self.storage)


    def get_next_position_id(self):
        return self.pool.getNextPositionId().onchain_view(storage=self.storage)


    def get_claim(self, event_id, position_id):
        key = {'eventId': event_id, 'positionId': position_id}
        return self.pool.getClaim(key).onchain_view(storage=self.storage)


    def get_withdrawal(self, withdrawal_id):
        return self.pool.getWithdrawal(withdrawal_id).onchain_view(storage=self.storage)


    def get_next_withdrawal_id(self):
        return self.pool.getNextWithdrawalId().onchain_view(storage=self.storage)


    def get_active_events(self):
        return self.pool.getActiveEvents().onchain_view(storage=self.storage)


    def get_event(self, event_id):
        return self.pool.getEvent(event_id).onchain_view(storage=self.storage)


    def is_deposit_paused(self):
        return self.pool.isDepositPaused().onchain_view(storage=self.storage)


    def get_entry_lock_period(self):
        return self.pool.getEntryLockPeriod().onchain_view(storage=self.storage)


    def get_manager(self):
        return self.pool.getManager().onchain_view(storage=self.storage)


    def get_total_shares(self):
        return self.pool.getTotalShares().onchain_view(storage=self.storage)


    def get_next_liquidity_f(self):
        return self.pool.getNextLiquidityF().onchain_view(storage=self.storage)


    def get_liquidity_units(self):
        return self.pool.getLiquidityUnits().onchain_view(storage=self.storage)


    def get_state_values(self):
        return self.pool.getStateValues().onchain_view(storage=self.storage)


    def wait(self, wait_time=0):
        self.current_time += wait_time

