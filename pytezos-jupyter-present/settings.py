settings = dict(
    SHELL_URL = 'https://florence-tezos.giganode.io/',
    # SHELL_URL = 'https://florencenet.smartpy.io',
    CONTRACT_ADDRESS = 'KT1Sr27vuBCx7au4e4yqvRdkgfYnyG3P4ekp',
    KEYS_DIRECTORY = 'test-keys',

    # default storage used to deploy new contract:
    DEFAULT_INITIAL_CONTRACT_STORAGE = {
        'betsAgainstLedger': 83876,
        'betsAgainstSum': 0,
        'betsForLedger': 83877,
        'betsForSum': 0,
        'closedRate': 0,
        'closedTime': 0,
        'currencyPair': 'XTZ-USD',
        'isBetsForWin': False,
        'isClosed': False,

        # edonet:
        # 'oracleAddress': 'KT1RCNpUEDjZAYhabjzgz1ZfxQijCDVMEaTZ',

        # florencenet:
        'oracleAddress': 'KT1SUP27JhX24Kvr11oUdWswk7FnCW78ZyUn',
        'targetRate': 0,
        'targetTime': 0
    },

    IS_ASYNC_ENABLED = False,
)
