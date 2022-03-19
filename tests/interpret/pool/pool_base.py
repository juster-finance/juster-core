from unittest import TestCase
import time
from os.path import dirname, join
from pytezos import ContractInterface, pytezos, MichelsonRuntimeError
from tests.test_data import (
    ONE_HOUR,
    ONE_DAY,
    generate_pool_storage,
    generate_line_params
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

        self.init_storage = generate_pool_storage(
            manager=self.manager,
            juster_address=self.juster_address
        )

        self.drop_changes()


    def drop_changes(self):
        self.storage = self.init_storage.copy()
        self.balances = {self.address: 0}
        self.next_event_id = 0


    def update_balance(self, address, amount):
        """ Used to track balances of different users """
        self.balances[address] = self.balances.get(address, 0) + amount


    def get_next_liquidity(self):
        """ Returns next event liquidity value in int """
        return int(
            self.storage['nextEventLiquidity'] / self.storage['precision'])

    def add_line(
            self,
            sender=None,
            currency_pair='XTZ-USD',
            max_active_events=2,
            bets_period=3600,
            last_bets_close_time=0,
            amount=0
        ):

        sender = sender or self.manager
        line_params = generate_line_params(
            currency_pair=currency_pair,
            max_active_events=max_active_events,
            bets_period=bets_period,
            last_bets_close_time=last_bets_close_time
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
        self.assertEqual(added_line['maxActiveEvents'], max_active_events)
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
            result.storage['entryLiquidity']
            - self.storage['entryLiquidity']
        )
        self.assertEqual(entry_liquidity_diff, amount)

        self.storage = result.storage
        self.update_balance(self.address, amount)
        self.update_balance(sender, -amount)

        return entry_id


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
        total_shares = self.storage['totalShares']
        total_liquidity = (
            self.balances['contract']
            + self.storage['activeLiquidity']
            - self.storage['withdrawableLiquidity']
            - self.storage['entryLiquidity']
        )

        is_new = total_shares == 0
        expected_added_shares = int(
            amount if is_new else amount / total_liquidity * total_shares)

        self.assertEqual(added_position['shares'], expected_added_shares)
        entry_liquidity_diff = (
            self.storage['entryLiquidity']
            - result.storage['entryLiquidity']
        )
        self.assertEqual(entry_liquidity_diff, amount)

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
        liquidity_diff = (
            self.storage['entryLiquidity'] - result.storage['entryLiquidity'])
        self.assertEqual(liquidity_diff, position['amount'])

        self.assertTrue(result.storage['entries'][entry_id] is None)
        result.storage['entries'].pop(entry_id)

        entry = self.storage['entries'][entry_id]
        self.assertEqual(len(result.operations), 1)
        op = result.operations[0]
        self.assertEqual(op['destination'], sender)
        self.assertEqual(op['amount'], str(entry['amount']))

        self.storage = result.storage


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

        position = self.storage['positions'][position_id]
        provided_liquidity_sum = 0

        for event_id in self.storage['activeEvents']:
            event = self.storage['events'][event_id]

            if position['addedCounter'] < event['createdCounter']:
                key = (event_id, position_id)
                default_claim = {'shares': 0}
                old_claim = self.storage['claims'].get(key, default_claim)

                if shares > 0:
                    new_claim = result.storage['claims'][key]

                    self.assertEqual(
                        new_claim['shares'] - old_claim['shares'],
                        shares)

                    provided_liquidity_sum += int(
                        event['provided'] * shares / event['totalShares'])

        old_position = self.storage['positions'][position_id]
        new_position = result.storage['positions'][position_id]
        is_should_be_removed = old_position['shares'] == shares

        if is_should_be_removed:
            self.assertTrue(new_position is None)
            result.storage['positions'].pop(position_id)
        else:
            self.assertEqual(old_position['provider'], new_position['provider'])
            self.assertEqual(new_position['provider'], sender)
            shares_diff = old_position['shares'] - new_position['shares']
            self.assertEqual(shares_diff, shares)
            self.assertEqual(
                new_position['addedCounter'], old_position['addedCounter'])
            total_shares_diff = (
                self.storage['totalShares'] - result.storage['totalShares'])
            self.assertEqual(total_shares_diff, shares)

        total_liquidity = (
            self.balances['contract']
            - self.storage['entryLiquidity']
            - self.storage['withdrawableLiquidity']
            + self.storage['activeLiquidity']
        )

        expected_amount = int(
            total_liquidity * shares / self.storage['totalShares']
            - provided_liquidity_sum)

        active_liquidity_diff = (
            self.storage['activeLiquidity']
            - result.storage['activeLiquidity']
        )

        self.assertEqual(active_liquidity_diff, provided_liquidity_sum)

        self.storage = result.storage

        # extracting amount if there are operations:
        if expected_amount:
            self.assertTrue(len(result.operations) == 1)
            op = result.operations[0]
            amount = int(op['amount'])
            self.assertEqual(expected_amount, amount)

            self.update_balance(self.address, -amount)
            self.update_balance(sender, amount)
            return amount

        return 0


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

        amounts = {}
        for position in positions:
            key = (position['eventId'], position['positionId'])
            self.assertTrue(result.storage['claims'][key] is None)
            result.storage['claims'].pop(key)

            claim = self.storage['claims'][key]
            event = self.storage['events'][position['eventId']]
            amount = int(claim['shares'] / event['totalShares'] * event['result'])
            provider = claim['provider']

            if amount > 0:
                amounts[provider] = amounts.get(provider, 0) + amount

        amounts_sum = sum(amounts.values())
        self.assertEqual(len(amounts), len(result.operations))

        withdrawable_diff = (
            self.storage['withdrawableLiquidity']
            - result.storage['withdrawableLiquidity']
        )
        self.assertEqual(withdrawable_diff, amounts_sum)
        self.storage = result.storage

        if amounts_sum:
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
        withdrawable_diff = (
            result.storage['withdrawableLiquidity']
            - self.storage['withdrawableLiquidity']
        )

        event = self.storage['events'][event_id]
        event_lock = int(event['lockedShares'] / event['totalShares'] * amount)
        self.assertEqual(withdrawable_diff, event_lock)

        self.storage = result.storage
        self.update_balance(sender, -amount)
        self.update_balance(self.address, amount)


    def create_event(self, sender=None, event_line_id=0, next_event_id=None, amount=0):
        sender = sender or self.manager
        next_event_id = next_event_id or self.next_event_id

        contract_call = self.pool.createEvent(event_line_id)
        result = contract_call.with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            view_results={
                f'{self.juster_address}%getNextEventId': next_event_id
            },
            balance=self.balances[self.address]
        )

        self.assertTrue(next_event_id in result.storage['activeEvents'])
        active_liquidity_diff = (
            result.storage['activeLiquidity']
            - self.storage['activeLiquidity']
        )
        self.assertEqual(active_liquidity_diff, self.get_next_liquidity())
        added_event = result.storage['events'][next_event_id]

        target_event = {
            'createdCounter': self.storage['counter'],
            'lockedShares': 0,
            'provided': self.get_next_liquidity(),
            'result': None,
            'totalShares': self.storage['totalShares']
        }

        self.assertDictEqual(added_event, target_event)

        self.assertEqual(self.storage['counter'] + 1, result.storage['counter'])
        self.storage = result.storage

        # two operations: one with newEvent and one provideLiquidity:
        self.assertEqual(len(result.operations), 2)

        event_fee = int(result.operations[0]['amount'])
        provide_op = int(result.operations[1]['amount'])
        amount = event_fee + provide_op

        self.assertEqual(event_fee, self.storage['newEventFee'])
        expected_provided = self.get_next_liquidity() - event_fee
        self.assertEqual(provide_op, expected_provided)

        self.update_balance(self.address, -amount)
        self.update_balance(self.juster_address, amount)
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
            result.storage['maxActiveEvents']
            - self.storage['maxActiveEvents']
        )

        self.assertEqual(
            abs(active_events_diff),
            self.storage['lines'][line_id]['maxActiveEvents'])

        next_event_liquidity_diff = (
            result.storage['nextEventLiquidity'] / result.storage['precision']
            - self.get_next_liquidity()
        )

        calculated_diff = int(
            self.get_next_liquidity()
            * self.storage['maxActiveEvents']
            / result.storage['maxActiveEvents']
        ) - self.get_next_liquidity()

        self.assertEqual(next_event_liquidity_diff, calculated_diff)

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


    def wait(self, wait_time=0):
        self.current_time += wait_time

