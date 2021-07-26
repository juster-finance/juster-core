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
            # creators=creators
        )

        data = self.endpoint(query, variables)
        events = data['data']['juster_event']

        if len(events):
            return self.deserialize_event(events[0])

        # TODO: what to do if there are no event found?
