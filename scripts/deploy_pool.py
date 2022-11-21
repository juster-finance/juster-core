# TODO make one deploy.py with CLI for both testnet/mainnet and different contracts
# TODO: separate configs for mainnet/testnet

import json

from pytezos import pytezos
from pytezos.contract.interface import ContractInterface

from scripts.helpers.pool import add_line
from scripts.helpers.pool import deploy_pool

SHELL = 'https://rpc.tzkt.io/ghostnet/'
KEY = 'key-ithaca.json'
CONTRACTS = {
    'pool': ContractInterface.from_file('build/contracts/pool.tz'),
}

# Juster address:
JUSTER_ADDRESS = 'KT1Feq9iRBBhpSBdPF1Y7Sd7iJu7uLqqRf1A'

# Event lines for multiple pools:
LINES_FN = 'scripts/event_lines/ghostnet.json'

with open('metadata/pool_metadata.json', 'r', encoding='utf8') as metadata_file:
    METADATA = json.loads(metadata_file.read())


if __name__ == '__main__':

    client = pytezos.using(key=KEY, shell=SHELL)

    with open(LINES_FN, 'r', encoding='utf8') as f:
        lines: dict = json.load(f)

    print(f'deploying {len(lines)} pools, one for each line')
    for line_params in lines:
        contract: ContractInterface = CONTRACTS['pool'].using(
            key=KEY, shell=SHELL
        )
        pool_address = deploy_pool(client, contract, line_params, METADATA)
        add_line(client, pool_address, line_params, JUSTER_ADDRESS)
