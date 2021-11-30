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

        self.juster_address = 'KT1SUP27JhX24Kvr11oUdWswk7FnCW78ZyUn'
        self.current_time = RUN_TIME

        self.init_storage = generate_line_aggregator_storage(
            manager=self.manager,
            juster_address=self.juster_address
        )

        self.storage = self.init_storage.copy()


    def add_line(self):
        line_params = generate_line_params()
        result = self.aggregator.addLine(line_params).interpret(
            storage=self.storage)

        # TODO: assert that storage changes was valid
        self.storage = result.storage


    def deposit_liqudiity(self):
        pass

    def claim_liquidity(self):
        pass

    def withdraw_liquidity(self):
        pass

    def pay_reward(self):
        pass

    def create_event(self):
        pass

