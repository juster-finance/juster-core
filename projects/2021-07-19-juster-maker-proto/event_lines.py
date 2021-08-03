import logging
import json
from tqdm import tqdm
from config import (
    DYNAMIC_PARAMS,
    CURRENCY_PAIRS,
    CREATORS
)
from utility import make_next_hour_timestamp


# TODO: I have feeling that somwthing is wrong with this func, maybe it should
# be inside JusterDipDupClient?
def get_last_bets_close_timestamp(dd, event_params):
    """ Makes query about the last event with similar to event_params
        to the dipdup endpoint and converts result to datetime

        This date is useful to understand when next event should be emitted
    """

    last_event = dd.query_last_line_event(
        event_params['currency_pair'],
        event_params['target_dynamics'],
        event_params['measure_period'],
        CREATORS
    )

    if last_event:
        last_date_created = int(last_event['bets_close_time'].timestamp())
        # TODO: it is possible that dipdup data have not indexed emitted events
        # if it was called right after last event was created. Is there is
        # a solution?
        return last_date_created

    else:
        hour_timestamp = make_next_hour_timestamp()
        self.logger.info(f'last bets close timestamp is not found: '
              + f'{event_params}, using next hour timestamp = {hour_timestamp}')
        return hour_timestamp


class EventLines:
    """ EventLines manage what kind of event types should be runned in
        Juster. It provides new lines generation and save/load of this events.
        This is collection of event params that should be generated
        with given frequency
    """

    dynamic_params = DYNAMIC_PARAMS


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
        with open('event_lines.json', 'r') as f:
            event_params = json.loads(f.read())

        new_event_lines = cls(event_params)
        return new_event_lines


    def save(self, filename):
        with open('event_lines.json', 'w') as f:
            f.write(json.dumps(self.event_params, indent=4))


    def update_timestamps(self, dd):
        """ Updates all event timestamps using DipDupClient """

        # updating events_params:
        for params in tqdm(self.event_params):
            params.update({
                'next_at': get_last_bets_close_timestamp(dd, params)
            })


    def get(self):
        return self.event_params


class EventLinesOnlyHours(EventLines):
    """ This is simplified Event Lines that used in debug/test purposes: """

    dynamic_params = [
        dict(period=3600,  target_dynamics=1.00, liquidity_percent=0.01),
        dict(period=3600,  target_dynamics=0.99, liquidity_percent=0.02),
        dict(period=3600,  target_dynamics=1.01, liquidity_percent=0.02),
    ]

