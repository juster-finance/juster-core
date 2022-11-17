def name_period(seconds):
    minutes = seconds // 60
    seconds = seconds % 60
    hours = minutes // 60
    minutes = minutes % 60
    days = hours // 24
    hours = hours % 24

    return ''.join([
        f'{days}D' if days > 0 else '',
        f'{hours}H' if hours > 0 else '',
        f'{minutes}M' if minutes > 0 else '',
        f'{seconds}S' if seconds > 0 else '',
    ])

assert name_period(3600) == '1H'
assert name_period(3600 * 6) == '6H'
assert name_period(30 * 60) == '30M'
assert name_period(1 * 60) == '1M'
assert name_period(3601) == '1H1S'
assert name_period(24*3600) == '1D'
assert name_period(72*3600) == '3D'
assert name_period(36*3600) == '1D12H'


def generate_pool_name(line_params):
    currency_pair = line_params['currency_pair']
    timeframe_seconds = line_params['measure_period']
    return f'{currency_pair}-{name_period(timeframe_seconds)}'

