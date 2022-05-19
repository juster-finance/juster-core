# Juster
This repository contains smart contracts for Juster protocol V1. This is [whitepaper](https://juster.fi/docs/whitepaper.pdf) implementation that allows to create price dynamic events using [Harbinger](https://github.com/tacoinfra/harbinger) price data oracle. This contract allows to create multiple events, configure event creation params, customize liquidity provider fees, control retained profit fees and more.

## Contracts
* [Juster](contracts/main/juster.ligo) - core contract that implements price dynamic events logic with internal constant product market maker
* [Pool](contracts/main/pool.ligo) - liquidity manager that allows to aggregate liquidity from different users and redistribute it to recurring events
* Token - [work in progress]
* Reward Program - [work in progress]

## Installation
This project managed by `poetry`. To install all dependencies run:
```console
make install
```

## Compilation
Contract compilation requires [ligo](https://ligolang.org/docs/intro/installation) compiler version `0.40.0` or higher. The easiest way to run LIGO is using docker. To compile all contracts:
```console
make compile
```

## Testing
All tests written using [PyTezos](https://pytezos.org/contents.html) python library. You need to have `python 3.10` or higher to run the tests. PyTezos [installation](https://pytezos.org/quick_start.html#installation) requires to have cryptographic libraries in system. This project using poetry to manage python packages. Before running tests you need to [install](#installation) all dependencies and [compile](#compilation) contracts. Then you can call:
```console
make test
```

## Deploying
There are python scripts in the `scripts` directory that allows to run contracts deployment:
```console
poetry shell
python scripts/deploy_juster.py
python scripts/deploy_pool.py
```

Note that you need to have `key.json` key file in your project root directory that will be used to deploy the contract. You can get one for test networks [here](https://teztnets.xyz/). Also make sure that your `ORACLE_ADDRESS` and `JUSTER_ADDRESS` constants refer to the contract you want to.

## Description
There are some flow charts that show Juster core contract implementation details:
* [Event life-cycle](docs/JUSTER-FLOW-event-lyfecycle.drawio.png)
* [Core entrypoints](docs/JUSTER-FLOW-juster-core.drawio.png)
* [Magement entrypoints](docs/JUSTER-FLOW-juster-management.drawio.png)

