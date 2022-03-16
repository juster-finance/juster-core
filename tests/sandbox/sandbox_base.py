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
from tests.test_data import (
    generate_juster_storage,
    generate_pool_storage
)


JUSTER_FN = '../../build/contracts/juster.tz'
POOL_FN = '../../build/contracts/pool.tz'
ORACLE_MOCK_FN = '../../build/mocks/oracle_mock.tz'
REWARD_PROGRAM_FN = '../../build/contracts/reward_program.tz'


def pkh(key):
    return key.key.public_key_hash()


class SandboxedJusterTestCase(SandboxedNodeTestCase):


    def _load_contract(self, client, contract_address):
        """ Load originated contract from blockchain """

        contract = client.contract(contract_address)
        contract = contract.using(
            shell=client.shell,
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

        filename = join(dirname(__file__), JUSTER_FN)
        contract = ContractInterface.from_file(filename)
        contract = contract.using(shell=client.shell, key=client.key)

        storage = generate_juster_storage(pkh(client), oracle_address)
        # the minimum event period params is setted to 1-sec because 1-sec blocks in sandbox:
        storage['config'].update({
            'minMeasurePeriod': 1,  # 1 block
            'minPeriodToBetsClose': 1,  # 1 block
            'maxAllowedMeasureLag': 100,  # 100 blocks
        })

        opg = contract.originate(initial_storage=storage)
        result = opg.send()
        self.bake_block()

        self.juster = self._find_contract_by_hash(client, result.hash())


    def _deploy_oracle_mock(self, client):
        """ Deploys Mock Oracle that used to test Juster """

        filename = join(dirname(__file__), ORACLE_MOCK_FN)
        contract = ContractInterface.from_file(filename)
        contract = contract.using(shell=client.shell, key=client.key)

        opg = contract.originate(initial_storage=5000000)
        result = opg.send()
        self.bake_block()

        self.oracle_mock = self._find_contract_by_hash(client, result.hash())


    def _deploy_pool(self, client, juster_address):
        """ Deploys Pool """

        filename = join(dirname(__file__), POOL_FN)
        contract = ContractInterface.from_file(filename)
        contract = contract.using(shell=client.shell, key=client.key)

        new_event_fee = (
            self.juster.storage['config']['expirationFee']()
            + self.juster.storage['config']['measureStartFee']()
        )

        storage = generate_pool_storage(
            manager=pkh(self.manager),
            juster_address=juster_address,
            new_event_fee=new_event_fee
        )

        opg = contract.originate(initial_storage=storage)
        result = opg.send()
        self.bake_block()

        self.pool = self._find_contract_by_hash(client, result.hash())


    def _deploy_reward_program(self, client, juster_address):
        """ Deploys Reward Program """

        filename = join(dirname(__file__), REWARD_PROGRAM_FN)
        contract = ContractInterface.from_file(filename)
        contract = contract.using(shell=client.shell, key=client.key)

        storage = dict(
            juster=juster_address,
            result=False
        )

        opg = contract.originate(initial_storage=storage)
        result = opg.send()
        self.bake_block()

        self.reward_program = self._find_contract_by_hash(client, result.hash())


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


    def _create_simple_event(self, client, bets_time=10):

        event_params = {
            'currencyPair': 'XTZ-USD',
            'targetDynamics': 1_000_000,
            'betsCloseTime': self.manager.now() + bets_time,
            'measurePeriod': 1,  # 1 block measure period
            'liquidityPercent': 0,
        }

        config = self.juster.storage['config']()
        amount = config['measureStartFee'] + config['expirationFee']

        opg = (client.contract(self.juster.address)
            .newEvent(event_params)
            .with_amount(amount)
            .send())
        self.bake_block()
        result = self._find_call_result_by_hash(client, opg.hash())


    def _provide_liquidity(
            self,
            event_id=0,
            user=None,
            amount=1_000_000,
            expected_below=None,
            expected_above_eq=None,
            max_slippage=1_000_000
        ):

        user = user or self.manager
        contract = user.contract(self.juster.address)

        event = contract.storage['events'][event_id]()
        expected_below = expected_below or event['poolBelow']
        expected_above_eq = expected_above_eq or event['poolAboveEq']

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
        participant_address = participant_address or pkh(user)

        opg = user.contract(self.juster.address).withdraw(
            eventId=event_id,
            participantAddress=participant_address
        ).send()

        return opg


    def _run_measurements(self, event_id=0, user=None):
        user = user or self.manager
        user.contract(self.juster.address).startMeasurement(event_id).send()
        self.bake_block()

        # TODO: get measurement time and wait K block?
        user.contract(self.juster.address).close(event_id).send()
        self.bake_block()

        self.assertTrue(self.juster.storage['events'][event_id]()['isClosed'])


    def _run_force_majeure(self, event_id=0, user=None):
        user = user or self.manager
        user.contract(self.juster.address).triggerForceMajeure(event_id).send()
        self.bake_block()


    def setUp(self):
        self._activate_accs()
        self._deploy_oracle_mock(self.manager)
        self._deploy_juster(self.manager, self.oracle_mock.address)
        self._deploy_pool(self.manager, self.juster.address)

