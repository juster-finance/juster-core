#include "../../partial/juster/juster_types.ligo"

(* Changing oracle to florencenet: *)
function lambda (var config : configType) : configType is
block {
    config.oracleAddress := ("KT1SUP27JhX24Kvr11oUdWswk7FnCW78ZyUn" : address);
} with config
