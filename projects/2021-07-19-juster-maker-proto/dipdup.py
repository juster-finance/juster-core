""" Very simple GraphQL querier """

from sgqlc.endpoint.http import HTTPEndpoint
from dateutil.parser import parse


class JusterDipDupClient:
    endpoint_uri = 'https://api.dipdup.net/juster/graphql'


    def __init__(self):

        self.last_line_event_query_text = self.read_query('queries/last_line_event.graphql')
        self.all_events_query_text = self.read_query('queries/all_events.graphql')

        self.endpoint = HTTPEndpoint(self.endpoint_uri)


    def read_query(self, filename):
        with open(filename, 'r') as f:
            return f.read()


    def deserialize_event(self, event):
        event['created_time'] = parse(event['created_time'])
        event['bets_close_time'] = parse(event['bets_close_time'])
        return event

    
    def query_all_events(self):

        query = self.all_events_query_text
        data = self.endpoint(query)
        events = data['data']['juster_event']

        events = [self.deserialize_event(event) for event in events]
        return events


    def query_last_line_event(self, currency_pair, target_dynamics, measure_period, creators):
        """ Requests last event in line with given params """

        query = self.last_line_event_query_text

        variables = dict(
            currency_pair=currency_pair,
            target_dynamics=target_dynamics,
            measure_period=measure_period,
            creators=creators
        )

        data = self.endpoint(query, variables)
        events = data['data']['juster_event']

        if len(events):
            return self.deserialize_event(events[0])

        # TODO: what to do if there are no event found?


# TODO: decide where should this function exist:
# (maybe split in parts and add to dd?)
def get_last_bets_close_timestamp(dd, event_params, creators, hour_timestamp=0):
    """ Makes query about the last event with similar to event_params
        to the dipdup endpoint and converts result to datetime

        This date is useful to understand when next event should be emitted
    """

    last_event = dd.query_last_line_event(
        event_params['currency_pair'],
        event_params['target_dynamics'],
        event_params['measure_period'],
        creators
    )

    # TODO: need to query creator address too, this is good to check if this address
    # within whitelist of our event creation system

    if last_event:
        last_date_created = int(last_event['bets_close_time'].timestamp())
        return last_date_created

    else:
        # TODO: make this into logs
        print(f'last bets close timestamp is not found: {event_params}, '
              + f'using default timestamp = {hour_timestamp}')
        return hour_timestamp
