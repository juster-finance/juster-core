import logging
import json


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


    def __init__(self, event_params=None):
        self.logger = logging.getLogger(__name__)
        self.event_params = event_params or []


    def generate_new(self):
        self.event_params = [
            {
                'currency_pair': currency_pair,
                'target_dynamics': params['target_dynamics'],
                'bets_period': params['period'],
                'measure_period': params['period'],
                'liquidity_percent': params['liquidity_percent'],
                'expiration_fee': 100_000,
                'measure_start_fee': 100_000
            } for currency_pair in CURRENCY_PAIRS
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

