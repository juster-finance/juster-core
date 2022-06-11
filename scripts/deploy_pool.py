# TODO make one deploy.py with CLI for both testnet/mainnet and different contracts

import time
from getpass import getpass

from pytezos import ContractInterface
from pytezos import pytezos

SHELL = 'https://rpc.tzkt.io/ithacanet/'
KEY = getpass()
CONTRACTS = {
    'pool': ContractInterface.from_file('build/contracts/pool.tz'),
}

# Juster address:
JUSTER_ADDRESS = 'KT1Feq9iRBBhpSBdPF1Y7Sd7iJu7uLqqRf1A'

with open('metadata/pool_metadata.json', 'r') as metadata_file:
    METADATA = metadata_file.read()


def to_hex(string):
    return string.encode().hex()


def generate_pool_storage(manager, juster_address):
    return {
        'nextLineId': 0,
        'lines': {},
        'activeEvents': {},
        'events': {},
        'positions': {},
        'nextPositionId': 0,
        'totalShares': 0,
        'claims': {},
        'manager': manager,
        'maxEvents': 0,
        'activeLiquidityF': 0,
        'withdrawableLiquidityF': 0,
        'entryLiquidityF': 0,
        'entryLockPeriod': 0,
        'entries': {},
        'nextEntryId': 0,
        'isDepositPaused': False,
        'metadata': {
            '': to_hex('tezos-storage:contents'),
            'contents': to_hex(METADATA),
        },
        'precision': 1_000_000,
        'proposedManager': manager,
        'liquidityUnits': 0,
        'withdrawals': {},
        'nextWithdrawalId': 0,
    }


def deploy_pool(client):
    print(f'deploying pool...')
    contract = CONTRACTS['pool'].using(key=KEY, shell=SHELL)
    storage = generate_pool_storage(
        manager=client.key.public_key_hash(), juster_address=JUSTER_ADDRESS
    )

    opg = contract.originate(initial_storage=storage).send()
    print(f'success: {opg.hash()}')
    client.wait(opg)

    # Searching for Pool contract address:
    opg = client.shell.blocks[-10:].find_operation(opg.hash())
    op_result = opg['contents'][0]['metadata']['operation_result']
    address = op_result['originated_contracts'][0]
    print(f'pool address: {address}')
    return address


if __name__ == '__main__':

    client = pytezos.using(key=KEY, shell=SHELL)
    juster_address = deploy_pool(client)
    # TODO: add basic lines
