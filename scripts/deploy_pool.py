# TODO make one deploy.py with CLI for both testnet/mainnet and different contracts
# TODO: separate configs for mainnet/testnet

from pytezos import pytezos
from pytezos.contract.interface import ContractInterface

from scripts.helpers.consts import CONTRACTS
from scripts.helpers.consts import JUSTER_ADDRESS
from scripts.helpers.consts import LINES
from scripts.helpers.consts import MANAGER_KEY
from scripts.helpers.consts import POOL_METADATA
from scripts.helpers.consts import SHELL
from scripts.helpers.pool import add_line
from scripts.helpers.pool import deploy_pool
from scripts.helpers.pool import generate_pool_name

if __name__ == '__main__':

    client = pytezos.using(key=MANAGER_KEY, shell=SHELL)

    print(f'deploying {len(LINES)} pools, one for each line')
    for line_params in LINES:
        contract: ContractInterface = CONTRACTS['pool'].using(
            key=client.key, shell=client.shell
        )
        pool_name = generate_pool_name(line_params)
        pool_address = deploy_pool(client, contract, pool_name, POOL_METADATA)
        add_line(client, pool_address, line_params, JUSTER_ADDRESS)
