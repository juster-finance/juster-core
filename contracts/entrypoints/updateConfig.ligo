function updateConfig(
    var updateConfigLambda : updateConfigParam;
    var store: storage) : (list(operation) * storage) is
block {
    if Tezos.sender =/= store.manager then
        failwith("Only contract manager can call updateConfig")
    else skip;

    const newEventConfig : newEventConfigType =
        updateConfigLambda(store.newEventConfig);
    store.newEventConfig := newEventConfig;

} with ((nil: list(operation)), store)
