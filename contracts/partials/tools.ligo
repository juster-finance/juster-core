(* Here collected various functions that are used by smart contract
    in different entrypoints, so it is not clear, where they should be placed
*)

function tezToNat(const t : tez) : nat is t / 1mutez;


function tezToInt(const t : tez) : int is int(tezToNat(t));


function natToTez(const t : nat) : tez is t * 1mutez;


function intToTez(const t : int) : tez is 
    if t >= 0 then natToTez(abs(t))
    else (failwith("Wrong intToTez amount (<0)") : tez);


(* Returns minimal value from two nat variables a & b *)
function minNat(const a : nat; const b : nat) : nat is
block {
    var minValue : nat := a;
    if (a > b) then minValue := b else skip;
} with minValue


(* Returns maximal value from two nat variables a & b *)
function maxNat(const a : nat; const b : nat) : nat is
block {
    var maxValue : nat := a;
    if (a < b) then maxValue := b else skip;
} with maxValue


function minTez(const a : tez; const b : tez) : tez is
natToTez(minNat(tezToNat(a), tezToNat(b)))


function roundDiv(const numerator: nat; const denominator: nat) : nat is
block {
    var result : nat := numerator / denominator;
    const remainder : nat = numerator mod denominator;
    const threshold : nat = denominator / 2n;
    if (remainder > threshold) then result := result + 1n else skip;
} with result


function getEvent(const s : storage; const eventId : nat) : eventType is
case Big_map.find_opt(eventId, s.events) of
| Some(event) -> event
| None -> (failwith("Event is not found") : eventType)
end;


function getReceiver(const a : address) : contract(unit) is
    case (Tezos.get_contract_opt(a): option(contract(unit))) of
    | Some (con) -> con
    | None -> (failwith ("Not a contract") : (contract(unit)))
    end;


(* Returns current amount of tez in ledger, if key is not in ledger return 0tez *)
function getLedgerAmount(const k : ledgerKey; const l : ledgerType) : tez is
block {
    var ledgerAmount : tez := 0tez;
    case Big_map.find_opt(k, l) of
    | Some(value) -> ledgerAmount := value
    | None -> ledgerAmount := 0tez
    end;
} with ledgerAmount


(* Returns current amount of nat in ledger, if key is not in ledger return 0 *)
function getNatLedgerAmount(const k : ledgerKey; const l : ledgerNatType) : nat is
block {
    var ledgerAmount : nat := 0n;
    case Big_map.find_opt(k, l) of
    | Some(value) -> ledgerAmount := value
    | None -> ledgerAmount := 0n
    end;
} with ledgerAmount


function makeCallToOracle(
    const eventId : nat;
    const s : storage;
    const entrypoint : callbackEntrypoint) : list(operation) is
block {

    const event = getEvent(s, eventId);
    const callToOracle : contract(oracleParam) =
        case (Tezos.get_entrypoint_opt("%get", event.oracleAddress) : option(contract(oracleParam))) of
        | None -> (failwith("No oracle found") : contract(oracleParam))
        | Some(con) -> con
        end;

    const callback : operation = Tezos.transaction(
        (event.currencyPair, entrypoint),
        0tez,
        callToOracle);
} with list[callback]


function prepareOperation(
    const addressTo : address;
    const payout : tez) : operation is

block {
    const receiver : contract(unit) = getReceiver(addressTo);
    const operation : operation = Tezos.transaction(unit, payout, receiver);
} with operation


(* Creates operation list with one operation if payout > 0tez, else returns
    empty list of operations: *)
function makeOperationsIfNotZero(
    const addressTo : address;
    const payout : tez) : list(operation) is
block {

    var operations : list(operation) := nil;
    (* Operation should be returned only if there are some amount to return: *)
    if payout > 0tez then
        operations := prepareOperation(addressTo, payout) # operations
    else skip;

} with operations


(* Checking that there are no amount included in operation: *)
function checkNoAmountIncluded(const p : unit) : unit is
block {
    if Tezos.amount > 0tez then
        failwith("Including tez using this entrypoint call is not allowed")
    else skip;
} with unit


function isHaveValueTez(const k : ledgerKey; const l : ledgerType) : bool is
    case Big_map.find_opt(k, l) of
    | Some(value) -> True
    | None -> False
    end


function isHaveValueNat(const k : ledgerKey; const l : ledgerNatType) : bool is
    case Big_map.find_opt(k, l) of
    | Some(value) -> True
    | None -> False
    end


function isParticipant(
    const store : storage;
    const key : ledgerKey) : bool is

    isHaveValueTez(key, store.betsAboveEq)
    or isHaveValueTez(key, store.betsBelow)
    or isHaveValueNat(key, store.liquidityShares)


function allowOnlyManager(const store : storage) : unit is
    if Tezos.sender =/= store.manager then
        failwith("Not a contract manager")
    else unit;
