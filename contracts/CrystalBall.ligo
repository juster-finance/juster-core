// type initializeType is unit
// type betType is unit
// type closeType is unit
// type closeCallbackType is unit
// type withdrawType is unit

type callbackReturnedValue is record [
    currencyPair : string;
    lastUpdate : timestamp;
    rate : nat
]

type callbackReturnedValueMichelson is michelson_pair_right_comb(callbackReturnedValue)
type oracleParam is string * contract(callbackReturnedValueMichelson)

type action is
// | Initialize of initializeType
| BetFor of unit
| BetAgainst of unit
| Close of unit
| CloseCallback of callbackReturnedValueMichelson
| Withdraw of unit

(* TODO: decide should it be accountBetType / betType or should it be two ledgers *)
type accountBetType is record [
    bet : tez;
    betType : nat; (* TODO: find the valid type *)
]

type storage is record [
    currencyPair : string;
    targetRate : nat;
    targetTime : timestamp;
    (* TODO: maybe it should be one ledger with record about bet type? *)
    betsForLedger : big_map(address, tez);
    betsAgainstLedger : big_map(address, tez);
    oracleAddress : address;
    adminAddress : address;
    debugTime : timestamp;
    debugRate : nat;
    (* TODO: calculate bets sum here *)
]

(*
function initialize(
    var currencyPair : string;
    var targetRate : nat;
    var targetTime : timestamp;
    var oracleAddress : address) : storage is
block {
    const newStorage : storage is record [
        currencyPair = currencyPair;
        targetRate = targetRate;
        targetTime = targetTime;
        betsForLedger = 
    ]
} with s
*)

function betFor(var s : storage) : storage is
block {
    (* TODO: if this sender already in ledger, it would overwrite amount, need to add this amount *)
    s.betsForLedger[Tezos.sender] := Tezos.amount;
} with s

function betAgainst(var s : storage) : storage is
block {
    (* TODO: if this sender already in ledger, it would overwrite amount, need to add this amount *)
    s.betsAgainstLedger[Tezos.sender] := Tezos.amount;
} with s

function close(var s : storage) : list(operation) is
block {

    const callToOracle : contract(oracleParam) =
        case (Tezos.get_entrypoint_opt("%get", s.oracleAddress) : option(contract(oracleParam))) of
        | None -> (failwith("NO_ORACLE_FOUND") : contract(oracleParam))
        | Some(con) -> con
        end;

    const op : operation = Tezos.transaction(
        ("XTZ-USD", (Tezos.self("%closeCallback") : contract(callbackReturnedValueMichelson))),
        0tez,
        callToOracle);

} with list[op]

function closeCallback(var p : callbackReturnedValueMichelson; var s : storage) : storage is
block {
    const param : callbackReturnedValue = Layout.convert_from_right_comb(p);
    s.debugTime := param.lastUpdate;
    s.debugRate := param.rate;
} with s

function main (var params : action; var s : storage) : (list(operation) * storage) is
case params of
// | Initialize(p) -> ((nil: list(operation)), s)  (* storage initialization can be made on deploy *)
| BetFor -> ((nil: list(operation)), betFor(s))
| BetAgainst -> ((nil: list(operation)), betAgainst(s))
| Close -> (close(s), s)
| CloseCallback(p) -> ((nil: list(operation)), closeCallback(p, s))
| Withdraw(p) -> ((nil: list(operation)), s)
end
