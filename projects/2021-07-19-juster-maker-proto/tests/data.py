from datetime import datetime


# TODO: should it be easier to have separate object with default constructor?
DEFAULT_EVENT_PARAMS = params = {
    'currency_pair': 'XTZ-USD',
    'target_dynamics': 1.0,
    'bets_period': 900,
    'measure_period': 900,
    'liquidity_percent': 0.01,
    'expiration_fee': 100_000,
    'measure_start_fee': 100_000,
    'bets_close_time': datetime.now()
}

