function updateConfig(
    const updateConfigLambda : updateConfigParam;
    var store: storage) : (list(operation) * storage) is
block {

    allowOnlyManager(store);

    const config : configType =
        updateConfigLambda(store.config);
    store.config := config;

} with ((nil: list(operation)), store)
