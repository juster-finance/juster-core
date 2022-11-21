from pytezos import pytezos
from pytezos.client import PyTezosClient
from pytezos.contract.interface import ContractInterface
from pytezos.operation.group import OperationGroup

from scripts.helpers.consts import CONTRACTS
from scripts.helpers.consts import JUSTER_METADATA_URI
from scripts.helpers.consts import MANAGER_KEY
from scripts.helpers.consts import ONE_DAY
from scripts.helpers.consts import ORACLE_ADDRESS
from scripts.helpers.consts import SHELL
from scripts.helpers.utility import to_hex


def generate_storage(manager: str, oracle_address: str) -> dict:
    config: dict = {
        'expirationFee': 100_000,
        'minLiquidityPercent': 0,
        'maxLiquidityPercent': 300_000,  # 30% for 1_000_000 liquidityPrecision
        'maxAllowedMeasureLag': 60 * 15,  # 15 minutes
        'maxMeasurePeriod': ONE_DAY * 31,  # 31 day
        'maxPeriodToBetsClose': ONE_DAY * 31,  # 31 day
        'measureStartFee': 100_000,
        'minMeasurePeriod': 60 * 5,  # 5 min
        'minPeriodToBetsClose': 60 * 5,  # 5 min
        'oracleAddress': oracle_address,
        'rewardCallFee': 100_000,
        'rewardFeeSplitAfter': ONE_DAY,
        'providerProfitFee': 10000,  # 1%
        'isEventCreationPaused': False,
    }

    storage: dict = {
        'events': {},
        'betsAboveEq': {},
        'betsBelow': {},
        'providedLiquidityAboveEq': {},
        'providedLiquidityBelow': {},
        'depositedLiquidity': {},
        'liquidityShares': {},
        'depositedBets': {},
        'nextEventId': 0,
        'closeCallId': None,
        'measurementStartCallId': None,
        'config': config,
        'manager': manager,
        'liquidityPrecision': 1_000_000,
        'ratioPrecision': 100_000_000,
        'sharePrecision': 100_000_000,
        'targetDynamicsPrecision': 1_000_000,
        'providerProfitFeePrecision': 1_000_000,
        'bakingRewards': 0,
        'retainedProfits': 0,
        'proposedManager': None,
        'isWithdrawn': {},
        'metadata': {"": to_hex(JUSTER_METADATA_URI)},
    }

    return storage


def activate_and_reveal(client: PyTezosClient) -> None:
    print(f'activating account {client.key.public_key_hash()}...')
    op: OperationGroup = client.activate_account().send()
    client.wait(op)

    op = client.reveal().send()
    client.wait(op)


def deploy_juster(client: PyTezosClient) -> str:
    print('deploying juster...')
    contract: ContractInterface = CONTRACTS['juster'].using(
        key=client.key, shell=client.shell
    )
    storage: dict = generate_storage(
        manager=client.key.public_key_hash(), oracle_address=ORACLE_ADDRESS
    )

    opg: OperationGroup = contract.originate(initial_storage=storage).send()
    print(f'success: {opg.hash()}')
    client.wait(opg)

    # Searching for Juster contract address:
    op: dict = client.shell.blocks[-10:].find_operation(
        operation_group_hash=opg.hash()
    )
    op_result: dict = op['contents'][0]['metadata']['operation_result']
    address: str = op_result['originated_contracts'][0]
    print(f'juster address: {address}')
    return address


if __name__ == '__main__':

    manager_client = pytezos.using(key=MANAGER_KEY, shell=SHELL)

    # 1. If key hasn't been used before, this function will allow to activate key:
    if manager_client.balance() < 1e-5:
        activate_and_reveal(manager_client)

    # 2. Juster deploy:
    juster_address = deploy_juster(manager_client)
