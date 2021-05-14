#include "../partials/types.ligo"

function lambda (var newEventConfig : newEventConfigType) : newEventConfigType is
block {
    const onePercent : nat = newEventConfig.liquidityPrecision / 100n;
    newEventConfig.liquidityPercent :=
        newEventConfig.liquidityPercent + onePercent;

} with newEventConfig
