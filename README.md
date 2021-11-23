# Juster
This repository contains smart contract for Juster protocol V1. This is [whitepaper](https://juster.fi/docs/whitepaper.pdf) implementation that allows to create price dynamic events using [Harbinger](https://github.com/tacoinfra/harbinger) price data oracle. This contract allows to create multiple events, configure event creation params, customize liquidity provider fees, control retained profit fees and more.

## Compilation
Contract compilation requires [ligo](https://ligolang.org/docs/intro/installation) compiler version `0.29.0` or higher. The easiest way to run LIGO is using docker:
```console
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.29.0 compile contract contracts/main/Juster.ligo -e main > build/tz/juster.tz
```

## Testing
All tests written using [PyTezos](https://pytezos.org/contents.html) python library. You need to have `python 3.10` or higher to run the tests. PyTezos [installation](https://pytezos.org/quick_start.html#installation) requires to have cryptographic libraries in system. To run tests it is also required to install `pytest`. Also you may prefere to work with [virtual enviroments](https://docs.python.org/3/library/venv.html) to prevent conflicts between different python projects.

There are some mock contracts and lambdas that used in tests, so it is required to compile them before running tests. There is prepared shell script that runs compilation process and then runs tests:
```console
./scripts/compile_and_test.sh
```

## Deploying
To deploy Juster contract it is required to have `python 3.10` or higher version in your system with [PyTezos 3.2.11](https://pytezos.org/quick_start.html#installation) or higher library installed. There are python script in the `scripts` directory that allows to run contract deployment:
```console
python scripts/deploy.py
```

Note that you need to have `key.json` key file in your project root directory that will be used to deploy the contract. You can get one for test networks [here](https://faucet.tzalpha.net/)

