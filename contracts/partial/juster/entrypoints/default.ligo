function default(
    const _param : unit;
    var store : storage) : (list (operation) * storage) is
block {

    store.bakingRewards := store.bakingRewards + Tezos.get_amount();

} with ((nil: list(operation)), store)
