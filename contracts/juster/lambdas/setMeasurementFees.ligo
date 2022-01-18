#include "../../partials/types.ligo"

function lambda (var config : configType) : configType is
block {
    config.expirationFee := 200_000mutez;
    config.measureStartFee := 200_000mutez;

} with config

