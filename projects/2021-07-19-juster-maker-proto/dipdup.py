""" Very simple GraphQL querier """

from sgqlc.endpoint.http import HTTPEndpoint
from dateutil.parser import parse
from utility import timestamp_to_date
import time
from config import DIPDUP_ENDPOINT_URI
from os.path import join


QUERIES_DIR = 'queries'
QUERIES = [
    'all_events',
    'canceled_to_withdraw',
    'last_line_event',
    # TODO: I don't like this "open_event_times" name!
    # maybe opened_events_force_majeure_check ?
    'open_event_times',
    'withdrawable_events'
]


class JusterDipDupClient:

    def __init__(self):

        self.queries = self.load_queries()
        self.endpoint = HTTPEndpoint(DIPDUP_ENDPOINT_URI)
        # TODO: any query to endpoint can fail with:
        # http.client.RemoteDisconnected: Remote end closed connection without response
        # need to find a way where to catch this errors and process them!
        # ALSO: urllib.error.URLError: <urlopen error [Errno -2] Name or service not known>
        # (this raises when connection is lost)


    def load_queries(self):
        """ Loads all queries from queries directory into dictionary """

        queries = {
            name: self.read_query(f'{join(QUERIES_DIR, name)}.graphql')
            for name in QUERIES}
        return queries


    def read_query(self, filename):
        with open(filename, 'r') as f:
            return f.read()


    def deserialize_event(self, event):
        if 'created_time' in event:
            event['created_time'] = parse(event['created_time'])

        if 'bets_close_time' in event:
            event['bets_close_time'] = parse(event['bets_close_time'])

        return event


    # TODO: rename make_event_query (?): if there would be another requests
    def make_query(self, query_name, **variables):
        """ Performs query to dipdup using `query_name`.graphql query from
            queries directory and variables passed as named arguments """

        query = self.queries[query_name]

        data = self.endpoint(query, variables)
        events = data['data']['juster_event']

        return [self.deserialize_event(event) for event in events]

