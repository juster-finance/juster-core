docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.38.1 compile contract contracts/main/reward_program.ligo -e main --protocol hangzhou > build/contracts/reward_program.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.38.1 compile contract contracts/main/pool.ligo -e main --protocol hangzhou > build/contracts/pool.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.38.1 compile contract contracts/main/oracle_mock.ligo -e main > build/mocks/oracle_mock.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.38.1 compile contract contracts/main/juster.ligo -e main --protocol ithaca > build/contracts/juster.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.38.1 compile expression pascaligo lambda --init-file "contracts/lambdas/juster/raise_liquidity_fee.ligo" > build/lambdas/raise_liq_fee.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.38.1 compile expression pascaligo lambda --init-file "contracts/lambdas/juster/reset_config.ligo" > build/lambdas/reset_new_event_config.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.38.1 compile expression pascaligo lambda --init-file "contracts/lambdas/juster/change_oracle.ligo" > build/lambdas/change_oracle.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.38.1 compile expression pascaligo lambda --init-file "contracts/lambdas/juster/trigger_pause_events.ligo" > build/lambdas/trigger_pause.tz
docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.38.1 compile expression pascaligo lambda --init-file "contracts/lambdas/juster/set_measurement_fees.ligo" > build/lambdas/set_measurement_fees.tz
pytest -v --ignore=projects

