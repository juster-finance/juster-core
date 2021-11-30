import unittest
from pytezos.sandbox.node import SandboxedNodeTestCase
from os.path import join, dirname
from pytezos import ContractInterface, pytezos
from tests.test_data import generate_juster_storage


JUSTER_FN = '../build/tz/juster.tz'


class SandboxedJusterTestCase(SandboxedNodeTestCase):

    def _deploy_juster(self):
        filename = join(dirname(__file__), JUSTER_FN)
        contract = ContractInterface.from_file(filename)
        contract = contract.using(
            shell=self.get_node_url(),
            key=self.client.key)

        initial_storage = generate_juster_storage(
            manager=self.client.key.public_key_hash(),
            oracle_address='KT1MwuujtBodVQFm1Jk1KTGNc49wygqoLvpe')

        opg = contract.originate(initial_storage=initial_storage)
        result = opg.send()
        self.bake_block()

        op = self.client.shell.blocks['head':].find_operation(result.hash())
        op_result = op['contents'][0]['metadata']['operation_result']
        address = op_result['originated_contracts'][0]

        self.juster = self.client.contract(address)


    def _create_event(self):

        event_params = {
            'currencyPair': 'XTZ-USD',
            'targetDynamics': 1_000_000,
            'betsCloseTime': self.client.now() + 1000,
            'measurePeriod': 300,
            'liquidityPercent': 0,
        }

        config = self.juster.storage['config']()
        amount = config['measureStartFee'] + config['expirationFee']

        opg = self.juster.newEvent(event_params).with_amount(amount).send()
        self.bake_block()


    def _add_liquidity(self):

        opg = self.juster.provideLiquidity(
            eventId=0,
            expectedRatioBelow=1,
            expectedRatioAboveEq=1,
            maxSlippage=1_000_000
        ).with_amount(1_000_000).send()

        self.bake_block()


    def setUp(self):
        self._deploy_juster()
        self._create_event()
        self._add_liquidity()


    @unittest.skip("this test fails with RpcError 404, need to find out why")
    def test_should_allow_to_bet_100_times(self):
        # fails after 19th bet:
        for number in range(100):
            print(f'betting {number}')
            opg = self.juster.bet(
                eventId=0,
                bet='aboveEq',
                minimalWinAmount=1_000
            ).with_amount(1_000).send()
            self.bake_block()

