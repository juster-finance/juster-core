""" Very simple GraphQL querier """

from sgqlc.endpoint.http import HTTPEndpoint
from dateutil.parser import parse


class JusterDipDupClient:
    endpoint_uri = 'https://api.dipdup.net/juster/graphql'


    def __init__(self):
        self.endpoint = HTTPEndpoint(self.endpoint_uri)

    
    def query_all_events(self):
        query = '''
            query QueryAllEvents {
              juster_event(order_by: {bets_close_time: desc}) {
                created_time
                bets_close_time
                id
                currency_pair {
                  symbol
                }
                measure_period
                target_dynamics
              }
            }
        '''

        data = self.endpoint(query)
        return data


    def query_last_events(self, currency_pair, target_dynamics, measure_period):
        """ Requests last event in line with given params """
    
        query = '''
            query MyQuery($target_dynamics: numeric = "1", $currency_pair: String = "BTC-USD", $measure_period: bigint = "3600") {
              juster_event(order_by: {bets_close_time: desc}, where: {currency_pair: {symbol: {_eq: $currency_pair}}, measure_period: {_eq: $measure_period}, target_dynamics: {_eq: $target_dynamics}}) {
                bets_close_time
                id
                currency_pair {
                  symbol
                }
                measure_period
                target_dynamics
                created_time
                status
                liquidity_percent
              }
            }
        '''

        variables = dict(
            currency_pair=currency_pair,
            target_dynamics=target_dynamics,
            measure_period=measure_period
        )
        data = self.endpoint(query, variables)
        return data


    def get_last_created_date(self, event_params):
        """ Makes query about the last event with similar to event_params
            to the dipdup endpoint and converts result to datetime """

        data = self.query_last_events(
            event_params['currency_pair'],
            event_params['target_dynamics'],
            event_params['measure_period'])

        # TODO: need to query creator address too, this is good to check if this address
        # within whitelist of our event creation system

        last_events = data['data']['juster_event']
        # TODO: check if there are any events found
        last_date_created = parse(last_events[0]['bets_close_time'])
        return last_date_created
