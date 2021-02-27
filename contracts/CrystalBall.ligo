type initializeType is unit
type betType is unit
type closeType is unit
type closeCallbackType is unit
type withdrawType is unit

type action is
| Initialize of initializeType
| Bet of betType
| Close of closeType
| CloseCallback of closeCallbackType
| Withdraw of withdrawType

(* TODO: decide should it be accountBetType / betType or should it be two ledgers *)
type accountBetType is record [
    bet : tez;
    betType : nat; (* TODO: find the valid type *)
]

type storage is record [
    currencyPair : string;
    targetRate : nat;
    targetTime : nat; (* TODO: need to understand what type should be for the time *)
    (* TODO: maybe it should be one ledger with record about bet type? *)
    betsForLedger : big_map(address, tez);
    betsAgainstLedger : big_map(address, tez);
    oracleAddress : address;
    adminAddress : address;
]

function main (var params : action; var s : storage) : (list(operation) * storage) is
case params of
| Initialize(p) -> ((nil: list(operation)), s)
| Bet(p) -> ((nil: list(operation)), s)
| Close(p) -> ((nil: list(operation)), s)
| CloseCallback(p) -> ((nil: list(operation)), s)
| Withdraw(p) -> ((nil: list(operation)), s)
end
