from unittest import TestCase
import time
from os.path import dirname, join
from pytezos import ContractInterface, pytezos, MichelsonRuntimeError
from tests.test_data import (
    ONE_HOUR,
    ONE_DAY,
    generate_line_aggregator_storage,
    generate_line_params
)

LINE_AGGREGATOR_FN = '../../../build/contracts/line_aggregator.tz'
RUN_TIME = int(time.time())


class LineAggregatorBaseTestCase(TestCase):
    """ Methods used to check different state transformations for Line Aggregator
        Each check method runs one transaction and then compare storage
        before and after transaction execution. At the end each check
        method returns new storage
    """

    def setUp(self):
        self.aggregator = ContractInterface.from_file(
            join(dirname(__file__), LINE_AGGREGATOR_FN))

        # four participants and their pk hashes:
        self.a = 'tz1iQE8ijR5xVPffBUPFubwB9XQJuyD9qsoJ'
        self.b = 'tz1MdaJfWzP5pPx3gwPxfdLZTHW6js9havos'
        self.c = 'tz1RS9GoEXakf9iyBmSaheLMcakFRtzBXpWE'
        self.d = 'tz1TdKuFwYgbPHHb7y1VvLH4xiwtAzcjwDjM'

        self.manager = self.a
        self.address = 'contract'

        self.juster_address = 'KT1SUP27JhX24Kvr11oUdWswk7FnCW78ZyUn'
        self.current_time = RUN_TIME

        self.init_storage = generate_line_aggregator_storage(
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


    def add_line(
            self,
            sender=None,
            currency_pair='XTZ-USD',
            max_active_events=2,
            bets_period=3600,
            last_bets_close_time=0
        ):

        sender = sender or self.manager
        line_params = generate_line_params(
            currency_pair=currency_pair,
            max_active_events=max_active_events,
            bets_period=bets_period,
            last_bets_close_time=last_bets_close_time
        )

        result = self.aggregator.addLine(line_params).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender
        )

        # TODO: assert that storage changes was valid
        # TODO: assert that line was added, that added time is correct that other params are correct
        self.storage = result.storage


    def deposit_liquidity(self, sender=None, amount=1_000_000):
        sender = sender or self.manager
        result = self.aggregator.depositLiquidity().with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            balance=self.balances[self.address] + amount
        )

        # TODO: assert that storage changes was valid
        entry_position_id = self.storage['nextEntryPositionId']
        self.storage = result.storage
        self.update_balance(self.address, amount)
        self.update_balance(sender, -amount)

        return entry_position_id


    def approve_liquidity(self, sender=None, entry_position_id=0):
        sender = sender or self.manager
        result = self.aggregator.approveLiquidity(entry_position_id).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            balance=self.balances[self.address]
        )

        # TODO: assert that storage changes was valid
        # TODO: assert that position added, that shares calculated properly, that time is correct
        self.assertTrue(result.storage['entryPositions'][entry_position_id] is None)
        result.storage['entryPositions'].pop(entry_position_id)
        self.storage = result.storage


    def claim_liquidity(self, sender=None, position_id=0, shares=1_000_000):
        sender = sender or self.manager
        params = {
            'positionId': position_id,
            'shares': shares
        }

        result = self.aggregator.claimLiquidity(params).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            balance=self.balances[self.address]
        )

        # TODO: assert that storage changes was valid
        # TODO: assert that position changed/removed, that shares calculated properly, that time is correct
        self.storage = result.storage

        # extracting amount if there are operations:
        if result.operations:
            self.assertTrue(len(result.operations) == 1)
            op = result.operations[0]
            amount = int(op['amount'])

            # TODO: assert that amount was calculated properly

            self.update_balance(self.address, -amount)
            self.update_balance(sender, amount)
            return amount

        return 0


    def withdraw_liquidity(self, sender=None, positions=None):
        sender = sender or self.manager
        positions = positions or [dict(positionId=0, eventId=0)]

        result = self.aggregator.withdrawLiquidity(positions).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            balance=self.balances[self.address]
        )

        # TODO: assert that storage changes was valid
        for position in positions:
            key = (position['eventId'], position['positionId'])
            self.assertTrue(result.storage['claims'][key] is None)
            result.storage['claims'].pop(key)

        self.storage = result.storage

        # TODO: extract amount:
        if result.operations:
            self.assertTrue(len(result.operations) == 1)
            op = result.operations[0]
            amount = int(op['amount'])

            # TODO: assert that amount was calculated properly

            self.update_balance(self.address, -amount)
            self.update_balance(sender, amount)
            return amount

        return 0


    def pay_reward(self, sender=None, event_id=0, amount=1_000_000):
        sender = sender or self.juster_address

        result = self.aggregator.payReward(event_id).with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            balance=self.balances[self.address]
        )

        # TODO: assert that storage changes was valid
        # TODO: assert that event removed from activeEvents, assert that withdrawnLiquidity calculated properly
        self.storage = result.storage
        self.update_balance(sender, -amount)
        self.update_balance(self.address, amount)


    def create_event(self, sender=None, event_line_id=0, next_event_id=None):
        sender = sender or self.manager
        next_event_id = next_event_id or self.next_event_id

        contract_call = self.aggregator.createEvent(event_line_id)
        result = contract_call.interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            view_results={
                f'{self.juster_address}%getNextEventId': next_event_id
            },
            balance=self.balances[self.address]
        )

        # TODO: assert that storage changes was valid
        # TODO: assert that event added to activeEvents, assert that event have correct liquidity amounts
        self.storage = result.storage

        # two operations: one with newEvent and one provideLiquidity:
        self.assertEqual(len(result.operations), 2)
        provide_op = result.operations[1]
        amount = int(provide_op['amount'])

        # TODO: check that amount calculated properly
        self.update_balance(self.address, -amount)
        self.update_balance(self.juster_address, amount)
        self.next_event_id += 1
        return next_event_id


    def wait(self, wait_time=0):
        self.current_time += wait_time

