docker run --rm -v "$PWD":"$PWD" -w "$PWD" ligolang/ligo:0.13.0 compile-contract contracts/CrystalBall.ligo main > pytezos-tests/crystal_ball.tz
pytest -v

