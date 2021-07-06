""" This tests is running inside sandbox env.
    Each bake_block() call increases time +1 sec so this test are performed
    in different time scales
"""

from pytezos.sandbox.node import SandboxedNodeTestCase
from pytezos.sandbox.parameters import sandbox_addresses, sandbox_commitment
from pytezos import ContractInterface, pytezos, MichelsonRuntimeError
from pytezos.rpc.errors import MichelsonError
from pytezos.contract.result import ContractCallResult
import unittest
from os.path import dirname, join
import json
from test_data import generate_storage


CONTRACT_FN = '../build/tz/juster.tz'


def pkh(key):
    return key.key.public_key_hash()


class ContractInteractionsTestCase(SandboxedNodeTestCase):


    def _load_contract(self, client, contract_address):
        """ Load originated contract from blockchain """

        contract = client.contract(contract_address)
        contract = contract.using(
            shell=self.get_node_url(),
            key=client.key)
        return contract


    def _find_contract_by_hash(self, client, opg_hash):
        """ Returns contract that was originated with opg_hash """

        op = client.shell.blocks['head':].find_operation(opg_hash)
        op_result = op['contents'][0]['metadata']['operation_result']
        address = op_result['originated_contracts'][0]

        return self._load_contract(client, address)


    def _deploy_juster(self, client, oracle_address):
        """ Deploys Juster with default storage  """

        filename = join(dirname(__file__), CONTRACT_FN)
        contract = ContractInterface.from_file(filename)
        contract = contract.using(shell=self.get_node_url(), key=client.key)

        storage = generate_storage(pkh(client), oracle_address)
        # the minimum event period params is setted to 1-sec because 1-sec blocks in sandbox:
        storage['config'].update({
            'minMeasurePeriod': 1,  # 1 block
            'minPeriodToBetsClose': 1,  # 1 block
        })

        opg = contract.originate(initial_storage=storage)
        result = opg.fill().sign().inject()
        self.bake_block()

        self.juster = self._find_contract_by_hash(client, result['hash'])


    def _find_call_result_by_hash(self, client, opg_hash):

        # Get injected operation and convert to ContractCallResult
        opg = client.shell.blocks['head':].find_operation(opg_hash)
        return ContractCallResult.from_operation_group(opg)[0]


    def _activate_accs(self):
        self.a = self.client.using(key='bootstrap1')
        self.a.reveal()

        self.b = self.client.using(key='bootstrap2')
        self.b.reveal()

        self.c = self.client.using(key='bootstrap3')
        self.c.reveal()

        self.manager = self.client.using(key='bootstrap4')
        self.manager.reveal()


    def _create_simple_event(self, client):
        event_params = {
            'currencyPair': 'XTZ-USD',
            'targetDynamics': 1_000_000,
            'betsCloseTime': 5,  # 5 blocks till close
            'measurePeriod': 1,  # 1 block measure period
            'liquidityPercent': 0,
        }

        config = self.juster.storage['config']()
        amount = config['measureStartFee'] + config['expirationFee']

        opg = (client.contract(self.juster.address)
            .newEvent(event_params)
            .with_amount(amount)
            .inject())
        self.bake_block()
        result = self._find_call_result_by_hash(client, opg['hash'])


    def setUp(self):
        self._activate_accs()
        # TODO: deploy oracle mock?
        oracle_address = 'KT1SUP27JhX24Kvr11oUdWswk7FnCW78ZyUn'
        self._deploy_juster(self.manager, oracle_address)


    def test_slippage(self):
        self._create_simple_event(self.manager)

        self.manager.contract(self.juster.address).provideLiquidity(
            eventId=0,
            expectedRatioBelow=1,
            expectedRatioAboveEq=1,
            maxSlippage=1000
        ).with_amount(1_000_000).inject()

        self.bake_block()

        # B bets in aboveEq:
        bet_res = self.b.contract(self.juster.address).bet(
            eventId=0,
            bet='aboveEq',
            minimalWinAmount=1_500_000
        ).with_amount(1_000_000).inject()

        # A provides liquidity after b made bet in the same block:
        pl_res = self.a.contract(self.juster.address).provideLiquidity(
            eventId=0,
            expectedRatioBelow=1,
            expectedRatioAboveEq=1,
            maxSlippage=1000
        ).with_amount(1_000_000).inject()

        self.bake_block()
        bet_res = self._find_call_result_by_hash(self.a, bet_res['hash'])

        with self.assertRaises(MichelsonError) as cm:
            pl_res = self._find_call_result_by_hash(self.a, pl_res['hash'])

        self.assertTrue(
            'Expected ratio very differs from current pool ratio'
            in str(cm.exception))
