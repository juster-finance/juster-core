function default(
    const param : unit;
    var store : storage) : (list (operation) * storage) is
block {

    store.bakingRewards := store.bakingRewards + Tezos.amount;

} with ((nil: list(operation)), store)
