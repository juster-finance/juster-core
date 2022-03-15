#include "../../partial/juster/juster_types.ligo"

function lambda (var config : configType) : configType is
block {
    const onePercent : nat = 10_000n;
    config.maxLiquidityPercent :=
        config.maxLiquidityPercent + onePercent;

} with config
