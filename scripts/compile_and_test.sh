docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.29.0 compile contract contracts/main/OracleMock.ligo -e main > build/tz/oracle_mock.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.29.0 compile contract contracts/main/Juster.ligo -e main > build/tz/juster.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.29.0 compile expression pascaligo lambda --init-file "contracts/lambdas/raiseLiquidityFee.ligo" > build/tz/lambda_raise_liq_fee.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.29.0 compile expression pascaligo lambda --init-file "contracts/lambdas/resetConfig.ligo" > build/tz/lambda_reset_new_event_config.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.29.0 compile expression pascaligo lambda --init-file "contracts/lambdas/changeOracle.ligo" > build/tz/lambda_change_oracle.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.29.0 compile expression pascaligo lambda --init-file "contracts/lambdas/triggerPauseEvents.ligo" > build/tz/lambda_trigger_pause.tz
pytest -v --ignore=projects

