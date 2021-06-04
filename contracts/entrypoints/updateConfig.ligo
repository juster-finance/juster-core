function updateConfig(
    const updateConfigLambda : updateConfigParam;
    var store: storage) : (list(operation) * storage) is
block {
    if Tezos.sender =/= store.manager then
        failwith("Only contract manager can call updateConfig")
    else skip;

    const config : configType =
        updateConfigLambda(store.config);
    store.config := config;

} with ((nil: list(operation)), store)
