# Creates test pools and runs interactions to make data for indexing and testing
import os
import sys

sys.path.append(os.path.join(sys.path[0], '..'))

import time

from pytezos import pytezos
from pytezos.client import PyTezosClient
from pytezos.contract.interface import ContractInterface

from scripts.helpers.consts import CONTRACTS
from scripts.helpers.consts import JUSTER_ADDRESS
from scripts.helpers.consts import MANAGER_KEY
from scripts.helpers.consts import POOL_METADATA
from scripts.helpers.consts import SHELL
from scripts.helpers.consts import USER_KEY
from scripts.helpers.pool import add_line
from scripts.helpers.pool import deploy_pool
from scripts.helpers.utility import try_multiple_times


def generate_line_params(juster_address: str) -> dict:
    return {
        "currency_pair": "XTZ-USD",
        "target_dynamics": 1.0,
        "bets_period": 300,
        "measure_period": 300,
        "liquidity_percent": 0.15,
        "expiration_fee": 100000,
        "measure_start_fee": 100000,
        "shift": 0,
        "pool_a_ratio": 1,
        "pool_b_ratio": 1,
    }


def deploy_test_contract_with_interactions(
    manager: PyTezosClient, user: PyTezosClient
) -> None:
    """Originating pool contract and making multiple interactions that allows
    to fill DipDup with data to test.
    Using time.sleep to wait for transaction to be accepted instead of .wait
    """

    print(f'originating contract with {manager.key.public_key_hash()}')
    contract: ContractInterface = CONTRACTS['pool'].using(
        key=manager.key, shell=manager.shell
    )

    pool_name: str = 'Test'
    pool_address = deploy_pool(manager, contract, pool_name, POOL_METADATA)
    time.sleep(60)

    manager_contract = manager.contract(pool_address)
    user_contract = user.contract(pool_address)

    manager_pkh: str = manager.key.public_key_hash()
    user_pkh: str = user.key.public_key_hash()

    print('depositing 1 xtz liquidity as entry_id: 0')
    _ = try_multiple_times(
        lambda: manager_contract.depositLiquidity()
        .with_amount(1_000_000)
        .send()
    )
    time.sleep(60)

    print('approving entry with entry_id: 0')
    _ = try_multiple_times(lambda: manager_contract.approveEntry(0).send())
    time.sleep(60)

    print(f'claiming all liquidity for {manager_pkh}')
    _ = try_multiple_times(
        lambda: manager_contract.claimLiquidity(
            provider=manager_pkh, shares=1_000_000
        ).send()
    )
    time.sleep(60)

    print('setting entry period to 60 secs')
    _ = try_multiple_times(
        lambda: manager_contract.setEntryLockPeriod(60).send()
    )
    time.sleep(60)

    print('depositing 10 xtz liquidity, entry_id: 1')
    _ = try_multiple_times(
        lambda: manager_contract.depositLiquidity()
        .with_amount(10_000_000)
        .send()
    )
    time.sleep(60)

    print('adding paused line with line_id: 0')
    line_params = generate_line_params(JUSTER_ADDRESS)
    add_line(
        manager_client,
        pool_address,
        line_params,
        JUSTER_ADDRESS,
        is_paused=True,
    )
    time.sleep(60)

    print('unpausing line_id: 0')
    _ = try_multiple_times(lambda: manager_contract.triggerPauseLine(0).send())
    time.sleep(60)

    print('adding unpaused line with line_id: 1')
    line_params = generate_line_params(JUSTER_ADDRESS)
    add_line(
        manager_client,
        pool_address,
        line_params,
        JUSTER_ADDRESS,
        is_paused=False,
    )
    time.sleep(60)

    print('pausing line_id: 0 again')
    _ = try_multiple_times(lambda: manager_contract.triggerPauseLine(0).send())
    time.sleep(60)

    print('approving entry with entry_id: 1')
    _ = try_multiple_times(lambda: manager_contract.approveEntry(1).send())
    time.sleep(60)

    print(f'claiming 50% liquidity for {manager_pkh}')
    _ = try_multiple_times(
        lambda: manager_contract.claimLiquidity(
            provider=manager_pkh, shares=5_000_000
        ).send()
    )
    time.sleep(60)

    print(f'claiming another 50% liquidity for {manager_pkh}')
    _ = try_multiple_times(
        lambda: manager_contract.claimLiquidity(
            provider=manager_pkh, shares=5_000_000
        ).send()
    )
    time.sleep(60)

    print('setting entry period to 0 secs')
    _ = try_multiple_times(
        lambda: manager_contract.setEntryLockPeriod(60).send()
    )
    time.sleep(60)

    print('depositing 0.1 xtz liquidity, entry_id: 2')
    _ = try_multiple_times(
        lambda: manager_contract.depositLiquidity().with_amount(100_000).send()
    )
    time.sleep(60)

    print('approving entry with entry_id: 2')
    _ = try_multiple_times(lambda: manager_contract.approveEntry(2).send())
    time.sleep(60)

    print('depositing 1 xtz liquidity, entry_id: 3 [will not be approved]')
    _ = try_multiple_times(
        lambda: manager_contract.depositLiquidity()
        .with_amount(1_000_000)
        .send()
    )
    time.sleep(60)

    print('giving 1 xtz to the pool')
    _ = try_multiple_times(
        lambda: manager_contract.default().with_amount(1_000_000).send()
    )
    time.sleep(60)

    print('running event for line_id: 1')
    _ = try_multiple_times(lambda: manager_contract.createEvent(1).send())
    time.sleep(60)

    print('triggering pause for deposits')
    _ = try_multiple_times(
        lambda: manager_contract.triggerPauseDeposit().send()
    )
    time.sleep(60)

    print('disband pool')
    _ = try_multiple_times(lambda: manager_contract.disband().send())
    time.sleep(60)

    print(f'claiming liquidity from {user_pkh}')
    _ = try_multiple_times(
        lambda: user_contract.claimLiquidity(
            provider=manager_pkh, shares=100_000
        ).send()
    )
    time.sleep(60)

    print('pausing line_id: 1 to turn this pool off')
    _ = try_multiple_times(lambda: manager_contract.triggerPauseLine(1).send())
    time.sleep(60)
    print('succeed')


def deploy_fake_contract_that_should_not_be_indexed(
    client: PyTezosClient,
) -> None:
    print(f'originating contract with {client.key.public_key_hash()}')
    contract: ContractInterface = CONTRACTS['pool'].using(
        key=client.key, shell=client.shell
    )

    pool_name: str = 'Fake Pool'
    pool_address = deploy_pool(client, contract, pool_name, POOL_METADATA)
    time.sleep(60)

    print('adding line with line_id: 0')
    line_params = generate_line_params(JUSTER_ADDRESS)
    add_line(
        client, pool_address, line_params, JUSTER_ADDRESS, is_paused=False
    )
    time.sleep(60)


if __name__ == '__main__':
    manager_client = pytezos.using(key=MANAGER_KEY, shell=SHELL)
    user_client = pytezos.using(key=USER_KEY, shell=SHELL)
    deploy_test_contract_with_interactions(manager_client, user_client)
    deploy_fake_contract_that_should_not_be_indexed(user_client)
