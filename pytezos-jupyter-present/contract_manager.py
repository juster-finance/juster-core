from pytezos.operation.result import OperationResult
from pprint import pprint


class ContractManager:

    def __init__(self, pytezos, settings):
        self.settings = settings
        self.contract_address = settings['CONTRACT_ADDRESS']
        self.is_async_enabled = settings['IS_ASYNC_ENABLED']
        self.pytezos = pytezos
        self.contract = self.pytezos.contract(self.contract_address)


    def create_new_storage(self, **kwargs):
        """ Creates new storage for Fortune Crystal Ball smart contract with
            custom storage params in kwargs
        """

        storage = self.settings['DEFAULT_INITIAL_CONTRACT_STORAGE'].copy()
        storage.update(kwargs)
        return storage


    def find_originated_contract_address(self, new_contract_result):
        """ Searches for new originated contract address in blockchain """

        op_hash, branch = new_contract_result['hash'], new_contract_result['branch']
        print(f'hash: {op_hash}, branch: {branch}')

        # blocks = self.pytezos.shell.blocks[branch:]
        blocks = self.pytezos.shell.blocks[-20:]
        opg = blocks.find_operation(op_hash)
        res = OperationResult.from_operation_group(opg)
        originated_contract_address = res[0].originated_contracts[0]
        return originated_contract_address


    def deploy_new_contract(self, **kwargs):
        """ Deploys new contract with params transfered in kwargs """

        new_storage = self.create_new_storage(**kwargs)
        print(f'Deploying new contract with storage:')
        pprint(new_storage)

        new_contract = self.pytezos.origination(
            script=self.contract.script(initial_storage=new_storage))
        new_contract = new_contract.autofill().sign().inject(_async=self.is_async_enabled)

        originated_contract_address = self.find_originated_contract_address(new_contract)
        print(f'Contract successfully originated at address: {originated_contract_address}')

        # return new contract manager with replaced contract address:
        new_settings = self.settings.copy()
        new_settings.update(CONTRACT_ADDRESS=originated_contract_address)

        # return ContractManager(self.pytezos, new_settings)
        return self.__class__(self.pytezos, new_settings)

    def use_instance(self, pytezos_instance):
        """ Returns copy of itself with another pytezos_instance """

        return self.__class__(pytezos_instance, self.settings)

    
class CrystalContractManager(ContractManager):
    """ Python interface to work with Crystal Contract """

    def bet_against(self, amount):
        transaction = self.contract.betAgainst().with_amount(amount).as_transaction()
        return transaction.autofill().sign().inject(_async=self.is_async_enabled)

    def bet_for(self, amount):
        transaction = self.contract.contract.betFor().with_amount(amount).as_transaction()
        return transaction.autofill().sign().inject(_async=self.is_async_enabled)

    def close(self):
        transaction = self.contract.close().as_transaction()
        return transaction.autofill().sign().inject(_async=self.is_async_enabled)

    def withdraw(self):
        transaction = self.contract.withdraw().as_transaction()
        return transaction.autofill().sign().inject(_async=self.is_async_enabled)
