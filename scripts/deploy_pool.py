# TODO make one deploy.py with CLI for both testnet/mainnet and different contracts

from pytezos import ContractInterface, pytezos
import time
from getpass import getpass

SHELL = 'https://rpc.tzkt.io/hangzhou2net/'
KEY = getpass()
CONTRACTS = {
    'pool': ContractInterface.from_file('build/contracts/pool.tz'),
}

# Hangzhou2 Juster address:
JUSTER_ADDRESS = 'KT197iHRJaAGw3oGpQj21YYV1vK9Fa5ShoMn'

# URI to metadata:
CONTRACT_METADATA_URI = 'ipfs://QmPC9ErX3VPa719nk3gJvRmoqdSo6KMAcnGeQ6BwvN8RML'


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
        'activeLiquidity': 0,
        'withdrawableLiquidity': 0,
        'claims': {},
        'manager': manager,
        'newEventFee': 400_000,
        'maxEvents': 0,
        'counter': 0,
        'nextLiquidity': 0,
        'entryLiquidity': 0,
        'entryLockPeriod': 0,
        'entries': {},
        'nextEntryId': 0,
        'isDepositPaused': False,
        'metadata': {"": to_hex(CONTRACT_METADATA_URI)},
        'precision': 1_000_000,
        'proposedManager': manager,
        'liquidityUnits': 0,
        'withdrawals': {},
        'nextWithdrawalId': 0
    }


def deploy_pool(client):
    print(f'deploying pool...')
    contract = CONTRACTS['pool'].using(key=KEY, shell=SHELL)
    storage = generate_pool_storage(
        manager=client.key.public_key_hash(),
        juster_address=JUSTER_ADDRESS)

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

