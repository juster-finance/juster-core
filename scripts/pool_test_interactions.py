# Creates test pools and runs interactions to make data for indexing and testing

import time
from helpers.pool import deploy_pool, add_line
from pytezos import ContractInterface
from pytezos import pytezos
from pytezos import PyTezosClient

SHELL = 'https://rpc.tzkt.io/ghostnet/'
KEY = 'key-ithaca.json'


def deploy_test_contract_with_interactions(client: PyTezosClient):
    return


def deploy_fake_contract_that_should_not_be_indexed(client: PyTezosClient):
    return


if __name__ == '__main__':

    client = pytezos.using(key=KEY, shell=SHELL)
    deploy_test_contract_with_interactions(client)
    deploy_fake_contract_that_should_not_be_indexed(client)
