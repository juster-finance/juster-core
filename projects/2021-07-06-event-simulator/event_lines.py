import logging
import json
from coinbase_api import CoinbaseAPI
from dynamics import calc_rate_by_freq_and_target


# Currency pairs that are used to create events:
CURRENCY_PAIRS = ['XTZ-USD', 'BTC-USD', 'ETH-USD']


class EventLines:
    """ EventLines manage what kind of event types should be runned in
        Juster. It provides new lines generation and save/load of this events.
        This is collection of event params that should be generated
        with given frequency
    """

    dynamic_params = [
        dict(period=3600,  target_dynamics=1.00, liquidity_percent=0.01),
        dict(period=3600,  target_dynamics=0.99, liquidity_percent=0.02),
        dict(period=3600,  target_dynamics=1.01, liquidity_percent=0.02),
        dict(period=21600, target_dynamics=1.00, liquidity_percent=0.01),
        dict(period=21600, target_dynamics=0.99, liquidity_percent=0.02),
        dict(period=21600, target_dynamics=1.01, liquidity_percent=0.02),
        dict(period=86400, target_dynamics=1.00, liquidity_percent=0.01),
        dict(period=86400, target_dynamics=0.99, liquidity_percent=0.02),
        dict(period=86400, target_dynamics=1.01, liquidity_percent=0.02),
    ]

    expiration_fee = 100_000
    measure_start_fee = 100_000


    def __init__(self, coinbase_api, event_params=None):
        self.logger = logging.getLogger(__name__)
        self.event_params = event_params or []
        self.api = coinbase_api
        self.update_coinbase_data()


    def update_coinbase_data(self):

        required_periods = {param['period'] for param in self.dynamic_params}

        self.coinbase_data = {
            pair: {
                period: self.api.get_history_prices(pair=pair, granularity=period)
                for period in required_periods
            } for pair in CURRENCY_PAIRS
        }


    def make_params(
        self, period, target_dynamics, liquidity_percent, currency_pair):

        df = self.coinbase_data[currency_pair][period]

        pool_a_ratio = calc_rate_by_freq_and_target(
            df, freq=f'{period}S', target_dynamics=target_dynamics)
        pool_b_ratio = 1 - pool_a_ratio

        return {
                'currency_pair': currency_pair,
                'target_dynamics': target_dynamics,
                'bets_period': period,
                'measure_period': period,
                'liquidity_percent': liquidity_percent,
                'expiration_fee': self.expiration_fee,
                'measure_start_fee': self.measure_start_fee,
                'pool_a_ratio': pool_a_ratio,
                'pool_b_ratio': pool_b_ratio
            }


    def generate_new(self):
        self.event_params = [
            self.make_params(
                period=params['period'],
                target_dynamics=params['target_dynamics'],
                liquidity_percent=params['liquidity_percent'],
                currency_pair=currency_pair,
            ) for currency_pair in CURRENCY_PAIRS
            for params in self.dynamic_params
        ]

        self.logger.info(f'generated {len(self.event_params)} event lines')
        return self.event_params


    @classmethod
    def load(cls, filename):
        with open(filename, 'r') as f:
            event_params = json.loads(f.read())

        new_event_lines = cls(event_params)
        return new_event_lines


    def save(self, filename):
        with open(filename, 'w') as f:
            f.write(json.dumps(self.event_params, indent=4))


    def get(self):
        return self.event_params


class EventLinesOnlyHours(EventLines):
    """ This is simplified Event Lines that used in debug/test purposes: """

    dynamic_params = [
        dict(period=3600,  target_dynamics=1.00, liquidity_percent=0.01),
        dict(period=3600,  target_dynamics=0.99, liquidity_percent=0.02),
        dict(period=3600,  target_dynamics=1.01, liquidity_percent=0.02),
    ]

