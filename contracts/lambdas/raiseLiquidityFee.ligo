#include "../partials/types.ligo"

function lambda (var newEventConfig : newEventConfigType) : newEventConfigType is
block {
    const onePercent : nat = 10_000n;
    newEventConfig.maxLiquidityPercent :=
        newEventConfig.maxLiquidityPercent + onePercent;

} with newEventConfig
