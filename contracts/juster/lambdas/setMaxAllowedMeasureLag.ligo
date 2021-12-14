#include "../partials/types.ligo"

function lambda (var config : configType) : configType is
block {
    config.maxAllowedMeasureLag := 9000n
} with config
