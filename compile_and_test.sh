docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.13.0 compile-contract contracts/main/BakingBet.ligo main > pytezos-tests/baking_bet.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.13.0 compile-contract contracts/lambdas/raiseLiquidityFee.ligo lambda > pytezos-tests/lambda_raise_liq_fee.tz
pytest -v

