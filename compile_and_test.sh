docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.13.0 compile-contract contracts/main/BakingBet.ligo main > build/tz/baking_bet.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.13.0 compile-expression pascaligo --init-file="contracts/lambdas/raiseLiquidityFee.ligo" lambda > build/tz/lambda_raise_liq_fee.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.13.0 compile-expression pascaligo --init-file="contracts/lambdas/resetNewEventConfig.ligo" lambda > build/tz/lambda_reset_new_event_config.tz
pytest -v

