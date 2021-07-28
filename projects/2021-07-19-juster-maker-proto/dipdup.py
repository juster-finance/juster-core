""" Very simple GraphQL querier """

from sgqlc.endpoint.http import HTTPEndpoint
from dateutil.parser import parse
from utility import timestamp_to_date
import time


class JusterDipDupClient:
    # TODO: move to config
    endpoint_uri = 'https://api.dipdup.net/juster/graphql'


    def __init__(self):

        self.last_line_event_query_text = self.read_query(
            'queries/last_line_event.graphql')
        self.all_events_query_text = self.read_query(
            'queries/all_events.graphql')
        self.withdrawable_events_query_text = self.read_query(
            'queries/withdrawable_events.graphql')
        self.open_event_times_query_text = self.read_query(
            'queries/open_event_times.graphql')

        self.endpoint = HTTPEndpoint(self.endpoint_uri)
        # TODO: any query to endpoint can fail with:
        # http.client.RemoteDisconnected: Remote end closed connection without response
        # need to find a way where to catch this errors and process them!
        # ALSO: urllib.error.URLError: <urlopen error [Errno -2] Name or service not known>
        # (this raises when connection is lost)


    def read_query(self, filename):
        with open(filename, 'r') as f:
            return f.read()


    def deserialize_event(self, event):
        if 'created_time' in event:
            event['created_time'] = parse(event['created_time'])

        if 'bets_close_time' in event:
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

    def query_withdrawable_events(self, closed_before):
        """ Requests list of events that have unwithdrawn positions and
            where time after close > rewardFeeSplitAfter (24h by default)
        """

        query = self.withdrawable_events_query_text
        variables = dict(closed_before=closed_before)

        data = self.endpoint(query, variables)
        events = data['data']['juster_event']

        if len(events):
            return [self.deserialize_event(event) for event in events]


    def query_open_event_times(self):

        query = self.open_event_times_query_text
        # TODO: add filter status in [NEW, STARTED]
        # so when they would be marked as isForceMajeure it would
        # not appear again in this request?

        # TODO: there are potential problem if there would be
        # too many opened events (>100). Then this request may return
        # only valid unclosed events. Maybe need to do some sorting
        # by event_id ASC for example

        data = self.endpoint(query)
        events = data['data']['juster_event']

        if len(events):
            return [self.deserialize_event(event) for event in events]
