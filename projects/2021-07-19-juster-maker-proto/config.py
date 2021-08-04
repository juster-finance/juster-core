import logging


# Configuring logger:
logging.basicConfig(
    filename='juster-maker.log',
    encoding='utf-8',
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

SHELL_URI = 'https://florencenet.smartpy.io'
# alternative: 'https://api.tez.ie/rpc/florencenet'
# alternative: 'https://florencenet-tezos.giganode.io'

JUSTER_ADDRESS = 'KT1CepDBrMg73d7LHm773KAsunjAjgLYituP'
DIPDUP_ENDPOINT_URI = 'https://api.dipdup.net/juster/graphql'

# Key used in pytezos:
KEY = '../test-keys/tz1fvzdyC7s4mMhBrmG38kasaZjE9PHPgFEu.json'

TRANSACTIONS_QUEUE_SIZE = 50

# Whitelist of the addresses that are used to manage Event Lines:
CREATORS = [
    'tz1iQE8ijR5xVPffBUPFubwB9XQJuyD9qsoJ',
    'tz1fvzdyC7s4mMhBrmG38kasaZjE9PHPgFEu'
]

""" Event line params are generated using CURRENCY_PAIRS and DYNAMIC_PAIRS
    and then saved into event_lines.json
    So it is possible to configure this events by editing event_lines.json and
    maybe it is wrong to have here another configurable params.
    TODO: it is better to have one params source: either this config either EVENT_LINES_PARAMS
"""

# Filename with stored event lines params:
EVENT_LINES_PARAMS_FN = 'event_lines.json'

# Currency pairs that are used to create events:
CURRENCY_PAIRS = ['XTZ-USD', 'BTC-USD', 'ETH-USD']

# For each currency pair there are 9 event lines generated:
DYNAMIC_PARAMS = [
    dict(period=3600,  target_dynamics=1.00, liquidity_percent=0.01),
    dict(period=3600,  target_dynamics=0.99, liquidity_percent=0.02),
    dict(period=3600,  target_dynamics=1.01, liquidity_percent=0.02),
    dict(period=21600, target_dynamics=1.00, liquidity_percent=0.01),
    dict(period=21600, target_dynamics=0.99, liquidity_percent=0.02),
    dict(period=21600, target_dynamics=1.01, liquidity_percent=0.02),
    dict(period=86400, target_dynamics=1.00, liquidity_percent=0.01),
    dict(period=86400, target_dynamics=0.99, liquidity_percent=0.02),
    dict(period=86400, target_dynamics=1.01, liquidity_percent=0.02),
]

# Period in seconds used to control update speed of the executors
EXECUTOR_UPDATE_PERIOD = 30

# Precision constants from contract:
DYNAMICS_PRECISION = 1_000_000
LIQUIDITY_PRECISION = 1_000_000

# After this period, withdraw caller would receive split:
REWARD_SPLIT_FEE_AFTER = 24*60*60

# Max slippage used in provide liquidity (10kk is 10%):
LIQUIDITY_MAX_SLIPPAGE = int(100_000_000 * 0.10)

# The amount of liquidity provided for each event:
PROVIDE_LIQUIDITY_AMOUNT = 1_000_000

# Max allowed time in seconds to be late in call startMeasurement / close:
MAX_ALLOWED_MEASURE_LAG = 4*60*60

