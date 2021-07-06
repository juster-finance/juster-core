""" Data for storage and params used to test contract """
import time

ONE_HOUR = 60*60
ONE_DAY = ONE_HOUR*24


def generate_storage(manager, oracle_address):
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
