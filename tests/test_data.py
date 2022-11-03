""" Data for storage and params used to test contract """

ONE_HOUR = 60 * 60
ONE_DAY = ONE_HOUR * 24


def generate_juster_config(
    oracle_address='KT1ENe4jbDE1QVG1euryp23GsAeWuEwJutQX',
    expiration_fee=100_000,
    measure_start_fee=200_000,
):
    return {
        'expirationFee': expiration_fee,
        'minLiquidityPercent': 0,
        'maxLiquidityPercent': 300_000,  # 30% for 1_000_000 liquidityPrecision
        'maxAllowedMeasureLag': ONE_HOUR * 4,  # 4 hours
        'maxMeasurePeriod': ONE_DAY * 31,  # 31 day
        'maxPeriodToBetsClose': ONE_DAY * 31,  # 31 day
        'measureStartFee': measure_start_fee,
        'minMeasurePeriod': 60 * 5,  # 5 min
        'minPeriodToBetsClose': 60 * 5,  # 5 min
        'oracleAddress': oracle_address,
        'rewardCallFee': 100_000,
        'rewardFeeSplitAfter': ONE_DAY,
        'providerProfitFee': 0,  # 0% for all tests that written before this fee
        'isEventCreationPaused': False,
    }


def generate_juster_storage(manager, oracle_address):
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
        'config': generate_juster_config(oracle_address),
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
        'metadata': {'': ''},
    }

    return storage


def generate_pool_storage(manager):
    return {
        'nextLineId': 0,
        'lines': {},
        'activeEvents': {},
        'events': {},
        'shares': {},
        'totalShares': 0,
        'activeLiquidityF': 0,
        'withdrawableLiquidityF': 0,
        'claims': {},
        'manager': manager,
        'maxEvents': 0,
        'entryLiquidityF': 0,
        'entryLockPeriod': 0,
        'entries': {},
        'nextEntryId': 0,
        'isDepositPaused': False,
        'metadata': {'': ''},
        'precision': 1_000_000,
        'proposedManager': manager,
        'liquidityUnits': 0,
        'withdrawals': {},
        'nextWithdrawalId': 0,
        'isDisbandAllow': False,
    }


def generate_line_params(
    bets_period=3600,
    measure_period=3600,
    currency_pair='XTZ_USD',
    max_events=2,
    target_dynamics=1_000_000,
    last_bets_close_time=0,
    juster_address='KT1D6XTy8oAHkUWdzuQrzySECCDMnANEchQq',
    min_betting_period=0,
    advance_time=0,
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
        'isPaused': False,
        'juster': juster_address,
        'minBettingPeriod': min_betting_period,
        'advanceTime': advance_time,
    }
