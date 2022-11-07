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
    METADATA = json.loads(metadata_file.read())


def to_hex(string):
    return string.encode().hex()


def generate_pool_storage(manager, juster_address, pool_name=None):
    metadata = METADATA.copy()
    if pool_name:
        metadata['name'] += f': {pool_name}'

    metadata_json = json.dumps(metadata)
    return {
        'nextLineId': 0,
        'lines': {},
        'activeEvents': {},
        'events': {},
        'shares': {},
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
            'contents': to_hex(metadata_json),
        },
        'precision': 1_000_000,
        'proposedManager': manager,
        'isDisbandAllow': False,
        'durationPoints': {},
        'totalDurationPoints': 0,
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
        except StopIteration as e:
            print(f'failed with StopIteration ({str(e)}), attempt #{attempt}')
            pass

    raise Exception('too many attempts')


def generate_pool_name(line_params):
    currency_pair = line_params['currency_pair']
    timeframe_seconds = line_params['measure_period']
    timeframe_hours = timeframe_seconds // 3600
    return f'{currency_pair}-{timeframe_hours}H'


def deploy_pool(client, line_params):
    contract = CONTRACTS['pool'].using(key=KEY, shell=SHELL)
    pool_name = generate_pool_name(line_params)
    print(f'deploying {pool_name} pool...')
    storage = generate_pool_storage(
        manager=client.key.public_key_hash(),
        juster_address=JUSTER_ADDRESS,
        pool_name=pool_name,
    )

    opg = try_multiple_times(
        lambda: contract.originate(initial_storage=storage).send()
    )
    print(f'success: {opg.hash()}')
    opg = try_multiple_times(
        lambda: client.wait(opg)
    )

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
    opg = try_multiple_times(
        lambda: client.wait(opg)
    )
    print(f'line succesfully added')


if __name__ == '__main__':

    client = pytezos.using(key=KEY, shell=SHELL)

    with open(LINES_FN, 'r') as f:
        lines = json.load(f)

    print(f'deploying {len(lines)} pools, one for each line')
    for line_params in lines:
        pool_address = deploy_pool(client, line_params)
        add_line(client, pool_address, line_params)

