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
        opg = contract.using(shell=self.get_node_url(), key=client.key)
        storage = generate_storage(pkh(client), oracle_address)
        opg = opg.originate(initial_storage=storage)
        result = opg.fill().sign().inject()
        self.bake_block()

        self.juster = self._find_contract_by_hash(client, result['hash'])


    '''
    def _find_call_result_by_hash(self, client, opg_hash):

        # Get injected operation and convert to ContractCallResult
        opg = client.shell.blocks['head':].find_operation(opg_hash)
        return ContractCallResult.from_operation_group(opg)[0]
    '''

    def _activate_accs(self):
        self.a = self.client.using(key='bootstrap1')
        self.a.reveal()

        self.b = self.client.using(key='bootstrap2')
        self.b.reveal()

        self.c = self.client.using(key='bootstrap3')
        self.c.reveal()

        self.manager = self.client.using(key='bootstrap4')
        self.manager.reveal()


    def setUp(self):
        self._activate_accs()
        # TODO: deploy oracle mock?
        oracle_address = 'KT1SUP27JhX24Kvr11oUdWswk7FnCW78ZyUn'
        self._deploy_juster(self.manager, oracle_address)


    def test_slippage(self):
        self.juster
        pass
