#include "../partials/types.ligo"

(* Changing oracle to florencenet: *)
function lambda (var newEventConfig : newEventConfigType) : newEventConfigType is
block {
    newEventConfig.oracleAddress := ("KT1SUP27JhX24Kvr11oUdWswk7FnCW78ZyUn" : address);
} with newEventConfig
