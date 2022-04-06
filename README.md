# Juster
This repository contains smart contracts for Juster protocol V1. This is [whitepaper](https://juster.fi/docs/whitepaper.pdf) implementation that allows to create price dynamic events using [Harbinger](https://github.com/tacoinfra/harbinger) price data oracle. This contract allows to create multiple events, configure event creation params, customize liquidity provider fees, control retained profit fees and more.

## Contracts
* [Juster](contracts/main/juster.ligo) - core contract that implements price dynamic events logic with internal constant product market maker
* [Pool](contracts/main/pool.ligo) - liquidity manager that allows to aggregate liquidity from different users and distribute it to recurring events
* Token - [work in progress]
* Reward Program - [work in progress]

## Compilation
Contract compilation requires [ligo](https://ligolang.org/docs/intro/installation) compiler version `0.38.1` or higher. The easiest way to run LIGO is using docker. To compile Juster core:
```console
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.38.1 compile contract contracts/main/juster.ligo -e main --protocol ithaca > build/contracts/juster.tz
```

Compiling Pool (using hangzhou protocol because ithaca does not support views yet):
```console
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.38.1 compile contract contracts/main/pool.ligo -e main --protocol hangzhou > build/contracts/pool.tz
```

There are some mock contracts and lambdas that used in tests, so it is required to compile them before running tests. There is prepared shell script that runs compilation process and then runs tests:
```console
./scripts/compile_and_test.sh
```

## Testing
All tests written using [PyTezos](https://pytezos.org/contents.html) python library. You need to have `python 3.10` or higher to run the tests. PyTezos [installation](https://pytezos.org/quick_start.html#installation) requires to have cryptographic libraries in system. To run tests it is also required to install `pytest`. Also you may prefere to work with [virtual enviroments](https://docs.python.org/3/library/venv.html) to prevent conflicts between different python projects.

There is known issue with running multiple sandbox tests: `node.validator.checkpoint_error RpcError`, to prevent this error sandbox tests can be runned separately, one by one:
```console
pytest tests/interpret/
pytest tests/sandbox/juster
pytest tests/sandbox/pool
```

## Deploying
To deploy Juster contract it is required to have `python 3.10` or higher version in your system with [PyTezos 3.4.1](https://pytezos.org/quick_start.html#installation) or higher library installed. There are python scripts in the `scripts` directory that allows to run contracts deployment:
```console
python scripts/deploy_juster.py
python scripts/deploy_pool.py
```

Note that you need to have `key.json` key file in your project root directory that will be used to deploy the contract. You can get one for test networks [here](https://teztnets.xyz/). Also make sure that your `ORACLE_ADDRESS` and `JUSTER_ADDRESS` constants refer to the contract you want to.

## Description
There are some flow charts that show Juster core contract implementation details:
* [Event life-cycle](docs/JUSTER-FLOW-event-lyfecycle.drawio.png)
* [Core entrypoints](docs/JUSTER-FLOW-juster-core.drawio.png)
* [Magement entrypoints](docs/JUSTER-FLOW-juster-management.drawio.png)

