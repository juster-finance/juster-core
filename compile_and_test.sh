docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.13.0 compile-contract contracts/main/BakingBet.ligo main > pytezos-tests/baking_bet.tz
pytest -v

