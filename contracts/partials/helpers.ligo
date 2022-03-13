function checkNoAmountIncluded(const _p : unit) : unit is
    if Tezos.amount > 0tez then
        failwith(Errors.disallowAmount)
    else unit;


(* TODO: maybe change it to checkSenderIs (but then what to do with error message) *)
function onlyManager(const manager : address) : unit is
    if Tezos.sender =/= manager then
        failwith(Errors.notManager)
    else unit;


function getOrFail(
    const key : _key;
    const ledger : big_map(_key, _value);
    const failwithMsg : string) : _value is
case Big_map.find_opt(key, ledger) of
| Some(value) -> value
| None -> (failwith(failwithMsg) : _value)
end;

