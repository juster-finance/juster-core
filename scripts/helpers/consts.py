# TODO: organize separate mainnet and testnet constant sets / configs:

import json

from pytezos.contract.interface import ContractInterface

ONE_HOUR = 60 * 60
ONE_DAY = ONE_HOUR * 24

SHELL = 'https://rpc.tzkt.io/ghostnet/'
MANAGER_KEY = 'keys/manager-key-ghostnet.json'
USER_KEY = 'key-ithaca.json'

CONTRACTS = {
    'pool': ContractInterface.from_file('build/contracts/pool.tz'),
    'juster': ContractInterface.from_file('build/contracts/juster.tz'),
}

# Ghostnet Harbinger normalizer address:
ORACLE_ADDRESS = 'KT1ENe4jbDE1QVG1euryp23GsAeWuEwJutQX'

# URI to metadata:
# TODO: consider using onchain metadata
JUSTER_METADATA_URI = 'ipfs://QmYVr7eBFXkW9uaFWs1jAX2CwrSdwFyZYrpE3Z2AbZSYY5'

# Juster ghostnet address:
JUSTER_ADDRESS = 'KT1Feq9iRBBhpSBdPF1Y7Sd7iJu7uLqqRf1A'

# Event lines for multiple pools:
LINES_FN = 'scripts/event_lines/ghostnet.json'

with open(LINES_FN, 'r', encoding='utf8') as f:
    LINES: dict = json.load(f)

with open(
    'metadata/pool_metadata.json', 'r', encoding='utf8'
) as metadata_file:
    POOL_METADATA = json.loads(metadata_file.read())
