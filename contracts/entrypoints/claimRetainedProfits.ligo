function claimRetainedProfits(
    const param : unit;
    var store : storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    var payout : tez := 0tez;
    if Tezos.sender = store.manager then block {
        payout := store.retainedProfits;
        store.retainedProfits := 0tez;
    } else failwith("Only contract manager allowed to claim retained profits");
    const operations : list(operation) = makeOperationsIfNotZero(Tezos.sender, payout);

} with (operations, store)
