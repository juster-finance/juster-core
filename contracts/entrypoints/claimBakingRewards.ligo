function claimBakingRewards(
    var param : unit;
    var store : storage) : (list(operation) * storage) is
block {

    var payout : tez := 0tez;
    if Tezos.sender = store.manager then block {
        payout := store.bakingRewards;
        store.bakingRewards := 0tez;
    } else failwith("Only contract manager allowed to claim baking rewards");
    const operations : list(operation) = makeOperationsIfNotZero(Tezos.sender, payout);

} with (operations, store)
