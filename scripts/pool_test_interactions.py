# Creates test pools and runs interactions to make data for indexing and testing

from pytezos import pytezos
from pytezos.client import PyTezosClient
from pytezos.contract.interface import ContractInterface

from scripts.helpers.consts import CONTRACTS
from scripts.helpers.consts import JUSTER_ADDRESS
from scripts.helpers.consts import KEY
from scripts.helpers.consts import POOL_METADATA
from scripts.helpers.consts import SHELL
from scripts.helpers.pool import add_line
from scripts.helpers.pool import deploy_pool


def deploy_test_contract_with_interactions(client: PyTezosClient) -> None:
    contract: ContractInterface = CONTRACTS['pool'].using(key=KEY, shell=SHELL)
    line_params = {}
    pool_address = deploy_pool(client, contract, line_params, POOL_METADATA)
    add_line(client, pool_address, line_params, JUSTER_ADDRESS)
    return


def deploy_fake_contract_that_should_not_be_indexed(
    client: PyTezosClient,
) -> None:
    return


if __name__ == '__main__':

    client_manager = pytezos.using(key=KEY, shell=SHELL)
    deploy_test_contract_with_interactions(client_manager)
    deploy_fake_contract_that_should_not_be_indexed(client_manager)
