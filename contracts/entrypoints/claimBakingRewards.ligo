function claimBakingRewards(
    const _param : unit;
    var store : storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);
    allowOnlyManager(store);

    const operations : list(operation) =
        makeOperationsIfNotZero(Tezos.sender, store.bakingRewards);
    store.bakingRewards := 0tez;

} with (operations, store)
