function setDelegate(
    var newDelegate : option (key_hash);
    var store : storage) : (list (operation) * storage) is
block {

    checkNoAmountIncluded(unit);
    const operations : list (operation) = list [Tezos.set_delegate(newDelegate)];

} with (operations, store)
