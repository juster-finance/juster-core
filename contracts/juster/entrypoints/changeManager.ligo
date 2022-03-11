function changeManager(
    const newManager : address;
    var store : storage) : (list (operation) * storage) is
block {

    checkNoAmountIncluded(unit);
    onlyManager(store.manager);
    store.proposedManager := Some(newManager);

} with ((nil: list(operation)), store)
