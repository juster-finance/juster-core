.DEFAULT_GOAL: all

LIGO_COMPILER = docker run --rm -v "${PWD}":"${PWD}" -w "${PWD}" ligolang/ligo:0.54.1

all: install lint compile test

install:
	poetry install

lint: isort black mypy pylint

mypy:
	poetry run mypy models/ tests/ scripts/

isort:
	poetry run isort tests/ models/ scripts/

pylint:
	poetry run pylint tests/ models/ scripts/

black:
	poetry run black models/ tests/ scripts/

test:
	poetry run pytest --ignore=projects

compile:
	${LIGO_COMPILER} compile contract contracts/main/reward_program.ligo -e main > build/contracts/reward_program.tz
	${LIGO_COMPILER} compile contract contracts/main/pool.ligo -e main > build/contracts/pool.tz
	${LIGO_COMPILER} compile contract contracts/main/oracle_mock.ligo -e main > build/mocks/oracle_mock.tz
	${LIGO_COMPILER} compile contract contracts/main/juster.ligo -e main > build/contracts/juster.tz
	${LIGO_COMPILER} compile expression pascaligo lambda --init-file "contracts/lambdas/juster/raise_liquidity_fee.ligo" > build/lambdas/raise_liq_fee.tz
	${LIGO_COMPILER} compile expression pascaligo lambda --init-file "contracts/lambdas/juster/reset_config.ligo" > build/lambdas/reset_new_event_config.tz
	${LIGO_COMPILER} compile expression pascaligo lambda --init-file "contracts/lambdas/juster/change_oracle.ligo" > build/lambdas/change_oracle.tz
	${LIGO_COMPILER} compile expression pascaligo lambda --init-file "contracts/lambdas/juster/trigger_pause_events.ligo" > build/lambdas/trigger_pause.tz
	${LIGO_COMPILER} compile expression pascaligo lambda --init-file "contracts/lambdas/juster/set_measurement_fees.ligo" > build/lambdas/set_measurement_fees.tz

