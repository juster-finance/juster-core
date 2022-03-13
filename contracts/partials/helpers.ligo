function checkNoAmountIncluded(const _p : unit) : unit is
    if Tezos.amount > 0tez
    then failwith(Errors.disallowAmount)
    else unit;


function checkSenderIs(
    const addr : address;
    const failwithMsg : string) : unit is

    if Tezos.sender =/= addr
    then failwith(failwithMsg)
    else unit;


function onlyManager(const manager : address) : unit is
    checkSenderIs(manager, Errors.notManager)


function getOrFail(
    const key : _key;
    const ledger : big_map(_key, _value);
    const failwithMsg : string) : _value is
case Big_map.find_opt(key, ledger) of
| Some(value) -> value
| None -> (failwith(failwithMsg) : _value)
end;

