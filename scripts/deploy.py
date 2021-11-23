from pytezos import ContractInterface, pytezos
import time

ONE_HOUR = 60*60
ONE_DAY = ONE_HOUR*24
SHELL = 'https://granadanet.smartpy.io/'
KEY_FILENAME = 'key.json'
CONTRACTS = {
    'juster': ContractInterface.from_file('build/tz/juster.tz'),
}

# Granadanet Harbinger normalizer address:
ORACLE_ADDRESS = 'KT1MwuujtBodVQFm1Jk1KTGNc49wygqoLvpe'


def generate_storage(manager, oracle_address):
    config = {
        'expirationFee': 100_000,
        'minLiquidityPercent': 0,
        'maxLiquidityPercent': 300_000,  # 30% for 1_000_000 liquidityPrecision
        'maxAllowedMeasureLag': 60*15,  # 15 minutes
        'maxMeasurePeriod': ONE_DAY*31,  # 31 day
        'maxPeriodToBetsClose': ONE_DAY*31,  # 31 day
        'measureStartFee': 100_000,
        'minMeasurePeriod': 60*5,  # 5 min
        'minPeriodToBetsClose': 60*5,  # 5 min
        'oracleAddress': oracle_address,
        'rewardCallFee': 100_000,
        'rewardFeeSplitAfter': ONE_DAY,
        'providerProfitFee': 10000,  # 1%
        'isEventCreationPaused': False
    }

    storage = {
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
        'proposedManager': None
    }

    return storage


def activate_and_reveal(client):
    print(f'activating account...')
    op = client.activate_account().send()
    client.wait(op)

    op = client.reveal().send()
    client.wait(op)


def deploy_juster(client):
    print(f'deploying juster...')
    contract = CONTRACTS['juster'].using(key=KEY_FILENAME, shell=SHELL)
    storage = generate_storage(
        manager=client.key.public_key_hash(),
        oracle_address=ORACLE_ADDRESS)

    opg = contract.originate(initial_storage=storage).send()
    print(f'success: {opg.hash()}')
    client.wait(opg)

    # Searching for Juster contract address:
    opg = client.shell.blocks['head':].find_operation(opg.hash())
    op_result = opg['contents'][0]['metadata']['operation_result']
    address = op_result['originated_contracts'][0]
    print(f'juster address: {address}')
    return address


if __name__ == '__main__':

    client = pytezos.using(key=KEY_FILENAME, shell=SHELL)

    """
    1. If key hasn't been used before, this function will allow to activate key:
    """
    if client.balance() < 1e-5:
        activate_and_reveal(client)

    """
    2. Juster deploy
    """
    juster_address = deploy_juster(client)

