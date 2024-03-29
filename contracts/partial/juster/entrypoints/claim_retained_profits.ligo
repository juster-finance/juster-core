function claimRetainedProfits(
    const _param : unit;
    var store : storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);
    onlyManager(store.manager);

    const operations : list(operation) =
        makeOperationsIfNotZero(store.manager, store.retainedProfits);
    store.retainedProfits := 0tez;

} with (operations, store)
