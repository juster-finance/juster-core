#include "../../partials/types.ligo"

function lambda (var config : configType) : configType is
block {
    config.expirationFee := 100_000mutez;
    config.measureStartFee := 100_000mutez;

} with config

