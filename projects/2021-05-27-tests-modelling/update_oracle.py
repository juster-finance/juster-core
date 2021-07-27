from pytezos import pytezos
import requests
import json
from pprint import pprint
import time

MAINNET_ORACLE = 'KT1Jr5t9UvGiqkvvsuUbPJHaYx24NzdUwNW9'
FLORENCENET_ORACLE = 'KT1PuT2NwwNjnxKy5XZEDZGHQNgdtLgN69i9'
FLORENCENET_NORMALIZER = 'KT1SUP27JhX24Kvr11oUdWswk7FnCW78ZyUn'


def detect_updates(op):
    is_entrypoint_update = op['parameter']['entrypoint'] == 'update'
    has_data = type(op['parameter']['value']) is dict
    return is_entrypoint_update and has_data


def prepare_update_params(update_params, pair='XTZ-USD'):
    # make it for multiple value pairs:
    value_params = update_params['parameter']['value'][pair]
    return {
        'XTZ-USD': [
            value_params['signature'],
            value_params['timestamp_0'],
            value_params['timestamp_1'],
            int(value_params['nat_0']),
            int(value_params['nat_1']),
            int(value_params['nat_2']),
            int(value_params['nat_3']),
            int(value_params['nat_4'])
        ]
    }


def get_last_update_params():
    response = requests.get(f'https://api.tzkt.io/v1/accounts/{MAINNET_ORACLE}/operations')
    data = json.loads(response.text)
    updates = [op for op in data if detect_updates(op)]
    params_no_names = prepare_update_params(updates[0])
    return params_no_names


def update_florencenet_oracle(cleint, params_no_names):
    oracle = cleint.contract(FLORENCENET_ORACLE)

    print('call oracle.update')
    transaction = oracle.update(params_no_names).as_transaction()
    transaction.autofill().sign().inject(_async=False)

    time.sleep(120)
    print('call oracle.push')
    transaction = oracle.push(f'{FLORENCENET_NORMALIZER}%update').as_transaction()
    transaction.autofill().sign().inject(_async=False)
    print('updated')


def main():
    client = pytezos.using(key='test-keys/tz1iQE8ijR5xVPffBUPFubwB9XQJuyD9qsoJ.json')

    while True:
        params = get_last_update_params()
        # TODO: check if params already updated in florence?
        print('last params to update:')
        pprint(params)
        update_florencenet_oracle(client, params)
        time.sleep(5*60)


if __name__ == '__main__':
    main()
