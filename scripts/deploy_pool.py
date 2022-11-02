# TODO make one deploy.py with CLI for both testnet/mainnet and different contracts
# TODO: separate configs for mainnet/testnet

import json
import time
from requests.exceptions import ConnectTimeout
from getpass import getpass

from pytezos import ContractInterface
from pytezos import pytezos

SHELL = 'https://rpc.tzkt.io/ghostnet/'
KEY = 'key-ithaca.json'
CONTRACTS = {
    'pool': ContractInterface.from_file('build/contracts/pool.tz'),
}

# Juster address:
JUSTER_ADDRESS = 'KT1Feq9iRBBhpSBdPF1Y7Sd7iJu7uLqqRf1A'

# Event lines for multiple pools:
LINES_FN = 'scripts/event_lines/ghostnet.json'

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
        'isDisbandAllow': False,
    }


def try_multiple_times(unstable_func, max_attempts=25):
    attempt = 0
    while attempt < max_attempts:
        try:
            attempt += 1
            return unstable_func()
        except ConnectTimeout as e:
            print(f'failed with ConnectionTimeout, attempt #{attempt}')
            pass

    raise Exception('too many attempts')


def deploy_pool(client):
    print(f'deploying pool...')
    contract = CONTRACTS['pool'].using(key=KEY, shell=SHELL)
    storage = generate_pool_storage(
        manager=client.key.public_key_hash(), juster_address=JUSTER_ADDRESS
    )

    opg = try_multiple_times(
        lambda: contract.originate(initial_storage=storage).send()
    )
    print(f'success: {opg.hash()}')
    client.wait(opg)

    # Searching for Pool contract address:
    opg = try_multiple_times(
        lambda: client.shell.blocks[-10:].find_operation(opg.hash())
    )
    op_result = opg['contents'][0]['metadata']['operation_result']
    address = op_result['originated_contracts'][0]
    print(f'pool address: {address}')
    return address


def convert_to_line_params(line):
    return {
        'betsPeriod': line['bets_period'],
        'currencyPair': line['currency_pair'],
        'isPaused': False,
        'lastBetsCloseTime': line['shift'],
        'liquidityPercent': int(line['liquidity_percent'] * 1_000_000),
        'maxEvents': 2,
        'measurePeriod': line['measure_period'],
        'rateAboveEq': line['pool_a_ratio'],
        'rateBelow': line['pool_b_ratio'],
        'targetDynamics': int(line['target_dynamics'] * 1_000_000),
        'juster': JUSTER_ADDRESS,
        'minBettingPeriod': 30*60,
        'advanceTime': 60
    }


def add_line(client, pool_address, line_params):
    print(f'adding line to {pool_address}, {line_params}')
    pool = client.contract(pool_address)
    opg = try_multiple_times(
        lambda: pool.addLine(convert_to_line_params(line_params)).send()
    )
    client.wait(opg)
    print(f'line succesfully added')


if __name__ == '__main__':

    client = pytezos.using(key=KEY, shell=SHELL)

    with open(LINES_FN, 'r') as f:
        lines = json.load(f)

    print(f'deploying {len(lines)} pools, one for each line')
    for line_params in lines:
        pool_address = deploy_pool(client)
        add_line(client, pool_address, line_params)

