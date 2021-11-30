function changeManager(
    const newManager : address;
    var store : storage) : (list (operation) * storage) is
block {

    checkNoAmountIncluded(unit);
    allowOnlyManager(store);
    store.proposedManager := Some(newManager);

} with ((nil: list(operation)), store)
