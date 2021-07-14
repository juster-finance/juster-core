import pandas as pd
from urllib.parse import urlencode
import requests
import json


class CoinbaseAPI:
    def __init__(self, uri='https://api.pro.coinbase.com'):
        self.uri = uri

    def get_history_prices(self, pair, start=None, stop=None, granularity=900):
        """ requests history data from coinbase, creates dataframe and makes
            all processing and type transformations """

        params = {
            'granularity': granularity
        }

        if start:
            params['start'] = start

        if stop:
            params['stop'] = stop

        method = f'{self.uri}/products/{pair}/candles?{urlencode(params)}'
        response = requests.get(method)
        headers = ['time', 'low', 'high', 'open', 'close', 'volume']
        df = pd.DataFrame(json.loads(response.text), columns=headers)

        df['time'] = pd.to_datetime(df['time'], unit='s')

        return df
