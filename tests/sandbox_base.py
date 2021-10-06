""" This tests is running inside sandbox env.
    Each bake_block() call increases time +1 sec so this test are performed
    in different time scales
"""

from pytezos.sandbox.node import SandboxedNodeTestCase
from pytezos.sandbox.parameters import sandbox_addresses, sandbox_commitment
from pytezos import ContractInterface, pytezos, MichelsonRuntimeError
from pytezos.contract.result import ContractCallResult
import unittest
from os.path import dirname, join
import json
from test_data import generate_storage


CONTRACT_FN = '../build/tz/juster.tz'


def pkh(key):
    return key.key.public_key_hash()


class SandboxedJusterTestCase(SandboxedNodeTestCase):


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

        self.blocks_till_close = 100
        event_params = {
            'currencyPair': 'XTZ-USD',
            'targetDynamics': 1_000_000,
            'betsCloseTime': self.blocks_till_close,
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


    def _provide_liquidity(
            self,
            event_id=0,
            user=None,
            amount=1_000_000,
            expected_below=None,
            expected_above_eq=None,
            max_slippage=1_000_000
        ):

        # TODO: get current ratio from contract
        expected_below = expected_below or expected_below
        expected_above_eq = expected_above_eq or expected_above_eq

        user = user or self.manager

        # TODO: make random amount
        # TODO: maybe it is better to make this not random but just _provide_liqudidity(random_amount)
        opg = user.contract(self.juster.address).provideLiquidity(
            eventId=event_id,
            expectedRatioBelow=expected_below,
            expectedRatioAboveEq=expected_above_eq,
            maxSlippage=max_slippage
        ).with_amount(amount).send()

        return opg


    def _bet(
            self,
            event_id=0,
            user=None,
            amount=1_000_000,
            side='aboveEq',
            minimal_win_amount=1_000_000
        ):

        user = user or self.manager
        opg = user.contract(self.juster.address).bet(
            eventId=event_id,
            bet=side,
            minimalWinAmount=minimal_win_amount
        ).with_amount(amount).send()

        return opg


    def _withdraw(self, event_id=0, user=None, participant_address=None):

        user = user or self.manager
        participant_address = pkh(user)

        opg = user.contract(self.juster.address).withdraw(
            eventId=event_id,
            participantAddress=participant_address
        ).with_amount().send()

        return opg


    def setUp(self):
        self._activate_accs()
        # TODO: deploy oracle mock?
        oracle_address = 'KT1SUP27JhX24Kvr11oUdWswk7FnCW78ZyUn'
        self._deploy_juster(self.manager, oracle_address)

