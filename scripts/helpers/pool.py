import json

from pytezos.client import PyTezosClient
from pytezos.contract.interface import ContractInterface
from pytezos.operation.group import OperationGroup

from scripts.helpers.utility import to_hex
from scripts.helpers.utility import try_multiple_times


def name_period(seconds: int) -> str:
    minutes = seconds // 60
    seconds = seconds % 60
    hours = minutes // 60
    minutes = minutes % 60
    days = hours // 24
    hours = hours % 24

    return ''.join(
        [
            f'{days}D' if days > 0 else '',
            f'{hours}H' if hours > 0 else '',
            f'{minutes}M' if minutes > 0 else '',
            f'{seconds}S' if seconds > 0 else '',
        ]
    )


assert name_period(3600) == '1H'
assert name_period(3600 * 6) == '6H'
assert name_period(30 * 60) == '30M'
assert name_period(1 * 60) == '1M'
assert name_period(3601) == '1H1S'
assert name_period(24 * 3600) == '1D'
assert name_period(72 * 3600) == '3D'
assert name_period(36 * 3600) == '1D12H'


def generate_pool_name(line_params: dict) -> str:
    currency_pair: str = line_params['currency_pair']
    timeframe_seconds: int = line_params['measure_period']
    return f'{currency_pair}-{name_period(timeframe_seconds)}'


def generate_pool_storage(
    manager: str, metadata: dict, pool_name=None
) -> dict:
    metadata = metadata.copy()
    if pool_name:
        metadata['name'] += f': {pool_name}'

    metadata_json: str = json.dumps(metadata)
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


def deploy_pool(
    client: PyTezosClient,
    contract: ContractInterface,
    line_params: dict,
    metadata: dict,
) -> str:
    pool_name = generate_pool_name(line_params)
    print(f'deploying {pool_name} pool...')
    storage = generate_pool_storage(
        manager=client.key.public_key_hash(),
        metadata=metadata,
        pool_name=pool_name,
    )

    opg: OperationGroup = try_multiple_times(
        lambda: contract.originate(initial_storage=storage).send()
    )
    print(f'success: {opg.hash()}')
    _ = try_multiple_times(lambda: client.wait(opg))

    # Searching for Pool contract address:
    op: dict = try_multiple_times(
        lambda: client.shell.blocks[-10:].find_operation(opg.hash())
    )
    op_result: dict = op['contents'][0]['metadata']['operation_result']
    address: str = op_result['originated_contracts'][0]
    print(f'pool address: {address}')
    return address


def convert_to_line_params(line, juster_address) -> dict:
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
        'juster': juster_address,
        'minBettingPeriod': 30 * 60,
        'advanceTime': 60,
    }


def add_line(
    client: PyTezosClient,
    pool_address: str,
    line_params: dict,
    juster_address: str,
) -> None:

    print(f'adding line to {pool_address}, {line_params}')
    pool = client.contract(pool_address)
    line_params = convert_to_line_params(line_params, juster_address)
    opg = try_multiple_times(lambda: pool.addLine(line_params).send())
    _ = try_multiple_times(lambda: client.wait(opg))
    print(f'line succesfully added, hash: {opg.hash()}')
