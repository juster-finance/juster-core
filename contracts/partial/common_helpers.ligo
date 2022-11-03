function checkNoAmountIncluded(const _p : unit) : unit is
    if Tezos.get_amount() > 0tez
    then failwith(Errors.disallowAmount)
    else unit;


function checkSenderIs(
    const addr : address;
    const failwithMsg : string) : unit is

    if Tezos.get_sender() =/= addr
    then failwith(failwithMsg)
    else unit;


function onlyManager(const manager : address) : unit is
    checkSenderIs(manager, Errors.notManager)


function getOrFail<keyType, valueType>(
    const key : keyType;
    const ledger : big_map(keyType, valueType);
    const failwithMsg : string) : valueType is
case Big_map.find_opt(key, ledger) of [
| Some(value) -> value
| None -> (failwith(failwithMsg) : valueType)
]


function getOrDefault<keyType, valueType>(
    const key : keyType;
    const ledger : big_map(keyType, valueType);
    const defaultValue : valueType) : valueType is
case Big_map.find_opt(key, ledger) of [
| Some(value) -> value
| None -> defaultValue
]


function getReceiver(const a : address) : contract(unit) is
    case (Tezos.get_contract_opt(a): option(contract(unit))) of [
    | Some (con) -> con
    | None -> (failwith ("Not a contract") : (contract(unit)))
    ]


function prepareOperation(
    const addressTo : address;
    const payout : tez
) : operation is Tezos.transaction(unit, payout, getReceiver(addressTo));


function ceilDiv(const numerator : nat; const denominator : nat) is
    case ediv(numerator, denominator) of [
    | Some(result, remainder) -> if remainder > 0n then result + 1n else result
    | None -> failwith("DIV / 0")
    ];
