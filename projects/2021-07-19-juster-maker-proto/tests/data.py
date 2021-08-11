from datetime import datetime


# TODO: should it be easier to have separate object with default constructor?
DEFAULT_EVENT_PARAMS = {
    'currency_pair': 'XTZ-USD',
    'target_dynamics': 1.0,
    'bets_period': 900,
    'measure_period': 900,
    'liquidity_percent': 0.01,
    'expiration_fee': 100_000,
    'measure_start_fee': 100_000,
    'bets_close_time': datetime.now()
}


DEFAULT_DIPDUP_EVENT_RESPONSE = {
    'data': {
        'juster_event': [{
            'created_time': '2021-08-09T11:00:50.357847+00:00',
            'bets_close_time': '2021-06-22T11:55:00+00:00'
        }]
    }
}

