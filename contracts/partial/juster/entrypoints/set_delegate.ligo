function setDelegate(
    const newDelegate : option (key_hash);
    var store : storage) : (list (operation) * storage) is
block {

    checkNoAmountIncluded(unit);
    onlyManager(store.manager);
    const operations : list (operation) = list [Tezos.set_delegate(newDelegate)];

} with (operations, store)
