""" Data for storage and params used to test contract """
import time

ONE_HOUR = 60*60
ONE_DAY = ONE_HOUR*24


def generate_juster_storage(manager, oracle_address):
    config = {
        'expirationFee': 100_000,
        'minLiquidityPercent': 0,
        'maxLiquidityPercent': 300_000,  # 30% for 1_000_000 liquidityPrecision
        'maxAllowedMeasureLag': ONE_HOUR*4,  # 4 hours
        'maxMeasurePeriod': ONE_DAY*31,  # 31 day
        'maxPeriodToBetsClose': ONE_DAY*31,  # 31 day
        'measureStartFee': 200_000,
        'minMeasurePeriod': 60*5,  # 5 min
        'minPeriodToBetsClose': 60*5,  # 5 min
        'oracleAddress': oracle_address,
        'rewardCallFee': 100_000,
        'rewardFeeSplitAfter': ONE_DAY,
        'providerProfitFee': 0,  # 0% for all tests that written before this fee
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
        'proposedManager': None,
        'isWithdrawn': {},
        'metadata': {'': ''}
    }

    return storage


def generate_pool_storage(manager, juster_address, new_event_fee=0):
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
        'juster': juster_address,
        'newEventFee': new_event_fee,
        'maxEvents': 0,
        'counter': 0,
        'nextLiquidity': 0,
        'entryLiquidity': 0,
        'entryLockPeriod': 0,
        'entries': {},
        'nextEntryId': 0,
        'isDepositPaused': False,
        'metadata': {'': ''},
        'precision': 1_000_000,
        'proposedManager': manager,
    }


def generate_line_params(
        bets_period=3600,
        measure_period=3600,
        currency_pair='XTZ_USD',
        max_events=2,
        target_dynamics=1_000_000,
        last_bets_close_time=0
    ):
    return {
        'currencyPair': currency_pair,
        'targetDynamics': target_dynamics,
        'liquidityPercent': 0,
        'rateAboveEq': 1,
        'rateBelow': 1,
        'measurePeriod': measure_period,
        'betsPeriod': bets_period,
        'lastBetsCloseTime': last_bets_close_time,
        'maxEvents': max_events,
        'isPaused': False
    }

