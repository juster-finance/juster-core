function acceptOwnership(
    const _param : unit;
    var store : storage) : (list (operation) * storage) is
block {

    checkNoAmountIncluded(unit);
    (* TODO: proposedManager can be just address that in not-proposed case
        is equal to the store.manager *)
    const proposedManager : address = case store.proposedManager of [
    | Some(proposed) -> proposed
    | None -> (failwith("Not allowed to accept ownership") : address)
    ];

    if proposedManager =/= Tezos.get_sender()
    then failwith("Not allowed to accept ownership")
    else skip;

    store.manager := proposedManager;
    store.proposedManager := (None : option(address));

} with ((nil: list(operation)), store)
