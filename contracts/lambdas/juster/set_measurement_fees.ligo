#include "../../partial/juster/juster_types.ligo"

function lambda (var config : configType) : configType is
block {
    config.expirationFee := 10_000mutez;
    config.measureStartFee := 10_000mutez;

} with config

