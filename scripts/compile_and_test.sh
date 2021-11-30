docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.29.0 compile contract contracts/line_aggregator/LineAggregator.ligo -e main --protocol hangzhou > build/contracts/line_aggregator.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.29.0 compile contract contracts/mocks/OracleMock.ligo -e main > build/mocks/oracle_mock.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.29.0 compile contract contracts/juster/Juster.ligo -e main > build/contracts/juster.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.29.0 compile expression pascaligo lambda --init-file "contracts/juster/lambdas/raiseLiquidityFee.ligo" > build/lambdas/raise_liq_fee.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.29.0 compile expression pascaligo lambda --init-file "contracts/juster/lambdas/resetConfig.ligo" > build/lambdas/reset_new_event_config.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.29.0 compile expression pascaligo lambda --init-file "contracts/juster/lambdas/changeOracle.ligo" > build/lambdas/change_oracle.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.29.0 compile expression pascaligo lambda --init-file "contracts/juster/lambdas/triggerPauseEvents.ligo" > build/lambdas/trigger_pause.tz
pytest -v --ignore=projects

