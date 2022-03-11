function checkNoAmountIncluded(const _p : unit) : unit is
    if Tezos.amount > 0tez then
        failwith(Errors.disallowAmount)
    else unit;


(* TODO: maybe change it to checkSenderIs (but then what to do with error message) *)
function onlyManager(const manager : address) : unit is
    if Tezos.sender =/= manager then
        failwith(Errors.notManager)
    else unit;


