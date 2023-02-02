# TODO: organize separate mainnet and testnet constant sets / configs:

import json

from pytezos.contract.interface import ContractInterface
from getpass import getpass

# Mainnet:
'''
SHELL = 'https://rpc.tzkt.io/mainnet/'
MANAGER_KEY = getpass('manager private key: ')
ORACLE_ADDRESS = 'KT1AdbYiPYb5hDuEuVrfxmFehtnBCXv4Np7r'
JUSTER_ADDRESS = 'KT1D6XTy8oAHkUWdzuQrzySECCDMnANEchQq'
LINES_FN = 'scripts/event_lines/mainnet-6h.json'
USER_KEY = getpass('user private key: ')
'''

# Ghostnet:
SHELL = 'https://rpc.tzkt.io/ghostnet/'
MANAGER_KEY = 'keys/manager-key-ghostnet.json'
ORACLE_ADDRESS = 'KT1ENe4jbDE1QVG1euryp23GsAeWuEwJutQX'
JUSTER_ADDRESS = 'KT1Feq9iRBBhpSBdPF1Y7Sd7iJu7uLqqRf1A'
LINES_FN = 'scripts/event_lines/mainnet-7d.json'
USER_KEY = 'keys/user-key-ghostnet.json'


ONE_HOUR = 60 * 60
ONE_DAY = ONE_HOUR * 24

CONTRACTS = {
    'pool': ContractInterface.from_file('build/contracts/pool.tz'),
    'juster': ContractInterface.from_file('build/contracts/juster.tz'),
}

# URI to metadata:
# TODO: consider using onchain metadata
JUSTER_METADATA_URI = 'ipfs://QmYVr7eBFXkW9uaFWs1jAX2CwrSdwFyZYrpE3Z2AbZSYY5'


with open(LINES_FN, 'r', encoding='utf8') as f:
    LINES: dict = json.load(f)

with open(
    'metadata/pool_metadata.json', 'r', encoding='utf8'
) as metadata_file:
    POOL_METADATA = json.loads(metadata_file.read())
