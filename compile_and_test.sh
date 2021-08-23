docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.23.0 compile-contract contracts/main/Token.ligo main > build/tz/token.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.23.0 compile-contract contracts/main/Juster.ligo main > build/tz/juster.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.23.0 compile-expression pascaligo --init-file="contracts/lambdas/raiseLiquidityFee.ligo" lambda > build/tz/lambda_raise_liq_fee.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.23.0 compile-expression pascaligo --init-file="contracts/lambdas/resetConfig.ligo" lambda > build/tz/lambda_reset_new_event_config.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.23.0 compile-expression pascaligo --init-file="contracts/lambdas/changeOracle.ligo" lambda > build/tz/lambda_change_oracle.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.23.0 compile-expression pascaligo --init-file="contracts/lambdas/triggerPauseEvents.ligo" lambda > build/tz/lambda_trigger_pause.tz
pytest -v

