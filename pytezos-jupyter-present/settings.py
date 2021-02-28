settings = dict(
    SHELL_URL = 'https://edonet-tezos.giganode.io/',
    # SHELL_URL = 'https://edonet.smartpy.io',
    CONTRACT_ADDRESS = 'KT1HbiznMedpC5BcQnUCUd5zCaXcemsU25Sk',
    KEYS_DIRECTORY = 'test-keys',

    # default storage used to deploy new contract:
    DEFAULT_INITIAL_CONTRACT_STORAGE = {
        'betsAgainstLedger': 0,
        'betsAgainstSum': 0,
        'betsForLedger': 0,
        'betsForSum': 0,
        'closedRate': 0,
        'closedTime': 0,
        'currencyPair': 'XTZ-USD',
        'isBetsForWin': False,
        'isClosed': False,

        # edonet:
        'oracleAddress': 'KT1RCNpUEDjZAYhabjzgz1ZfxQijCDVMEaTZ',

        # delphinet:
        # 'oracleAddress': 'KT1Age13nBE2VXxTPjwVJiE8Jbt73kumwxYx',
        'targetRate': 0,
        'targetTime': 0
    },

    IS_ASYNC_ENABLED = False,
)
