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


# TODO: decide where should this function exist:
# (maybe split in parts and add to dd?)
def get_last_bets_close_timestamp(dd, event_params, hour_timestamp=0):
    """ Makes query about the last event with similar to event_params
        to the dipdup endpoint and converts result to datetime

        This date is useful to understand when next event should be emitted
    """

    data = dd.query_last_events(
        event_params['currency_pair'],
        event_params['target_dynamics'],
        event_params['measure_period'])

    # TODO: need to query creator address too, this is good to check if this address
    # within whitelist of our event creation system

    last_events = data['data']['juster_event']

    if len(last_events):
        last_date_created = parse(last_events[0]['bets_close_time'])
        timestamp = int(last_date_created.timestamp())

        return timestamp

    else:
        # TODO: make this into logs
        print(f'last bets close timestamp is not found: {event_params}, '
              + f'using default timestamp = {hour_timestamp}')
        return hour_timestamp
