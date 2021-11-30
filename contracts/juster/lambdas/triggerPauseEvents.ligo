#include "../../partials/types.ligo"

function lambda (var config : configType) : configType is
block {
    config.isEventCreationPaused := not config.isEventCreationPaused;
} with config
