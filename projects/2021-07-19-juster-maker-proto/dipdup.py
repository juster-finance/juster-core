""" Very simple GraphQL querier """

from sgqlc.endpoint.http import HTTPEndpoint
from dateutil.parser import parse
from utility import timestamp_to_date, repeat_until_succeed
import time
from os.path import join
from urllib.error import URLError
from http.client import RemoteDisconnected


# TODO: move this params to config or not?
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

    def __init__(self, config):

        self.config = config
        self.queries = self.load_queries()
        self.endpoint = HTTPEndpoint(config.DIPDUP_ENDPOINT_URI)


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
    async def make_query(self, query_name, **variables):
        """ Performs query to dipdup using `query_name`.graphql query from
            queries directory and variables passed as named arguments """

        # TODO: find a way to throttle calls (limit to 1 per second for ex)
        query = self.queries[query_name]

        async def request():
            return self.endpoint(query, variables)

        # Running query and ignoring internet connection errors:
        data = await repeat_until_succeed(
            func=request,
            allowed_exceptions=[URLError, RemoteDisconnected],
            max_attempts=self.config.MAX_RETRY_ATTEMPTS,
            wait_after_fail=self.config.WAIT_AFTER_FAIL
        )

        events = data['data']['juster_event']

        return [self.deserialize_event(event) for event in events]

