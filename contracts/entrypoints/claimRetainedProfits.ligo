function claimRetainedProfits(
    const param : unit;
    var store : storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);
    allowOnlyManager(store);

    const operations : list(operation) =
        makeOperationsIfNotZero(Tezos.sender, store.retainedProfits);
    store.retainedProfits := 0tez;

} with (operations, store)
