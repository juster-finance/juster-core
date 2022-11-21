# Creates test pools and runs interactions to make data for indexing and testing

from pytezos import ContractInterface
from pytezos import PyTezosClient
from pytezos import pytezos

from scripts.helpers.pool import add_line
from scripts.helpers.pool import deploy_pool

SHELL = 'https://rpc.tzkt.io/ghostnet/'
KEY = 'key-ithaca.json'


def deploy_test_contract_with_interactions(client: PyTezosClient):
    return


def deploy_fake_contract_that_should_not_be_indexed(client: PyTezosClient):
    return


if __name__ == '__main__':

    client_manager = pytezos.using(key=KEY, shell=SHELL)
    deploy_test_contract_with_interactions(client_manager)
    deploy_fake_contract_that_should_not_be_indexed(client_manager)
