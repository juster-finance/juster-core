(* Here collected various functions that are used by smart contract
    in different entrypoints, so it is not clear, where they should be placed
*)

function tezToNat(var t : tez) : nat is t / 1mutez;


function natToTez(var t : nat) : tez is t * 1mutez;


(* Returns minimal value from two nat variables a & b *)
function minNat(var a : nat; var b : nat) : nat is
block {
    var minValue : nat := a;
    if (a > b) then minValue := b else skip;
} with minValue


function minTez(var a : tez; var b : tez) : tez is
natToTez(minNat(tezToNat(a), tezToNat(b)))


function roundDiv(var numerator: nat; var denominator: nat) : nat is
block {
    var result : nat := numerator / denominator;
    const remainder : nat = numerator mod denominator;
    const threshold : nat = denominator / 2n;
    if (remainder > threshold) then result := result + 1n else skip;
} with result


function getEvent(var s : storage; var eventId : nat) : eventType is
case Big_map.find_opt(eventId, s.events) of
| Some(event) -> event
| None -> (failwith("Event is not found") : eventType)
end;


function getReceiver(var a : address) : contract(unit) is
    case (Tezos.get_contract_opt(a): option(contract(unit))) of
    | Some (con) -> con
    | None -> (failwith ("Not a contract") : (contract(unit)))
    end;


(* Returns current amount of tez in ledger, if key is not in ledger return 0tez *)
function getLedgerAmount(var k : ledgerKey; var l : ledgerType) : tez is
block {
    var ledgerAmount : tez := 0tez;
    case Big_map.find_opt(k, l) of
    | Some(value) -> ledgerAmount := value
    | None -> ledgerAmount := 0tez
    end;
} with ledgerAmount


(* Returns current amount of nat in ledger, if key is not in ledger return 0 *)
function getNatLedgerAmount(var k : ledgerKey; var l : ledgerNatType) : nat is
block {
    var ledgerAmount : nat := 0n;
    case Big_map.find_opt(k, l) of
    | Some(value) -> ledgerAmount := value
    | None -> ledgerAmount := 0n
    end;
} with ledgerAmount


function makeCallToOracle(
    var eventId : nat;
    var s : storage;
    var entrypoint : callbackEntrypoint) : list(operation) is
block {

    const event = getEvent(s, eventId);
    const callToOracle : contract(oracleParam) =
        case (Tezos.get_entrypoint_opt("%get", s.oracleAddress) : option(contract(oracleParam))) of
        | None -> (failwith("No oracle found") : contract(oracleParam))
        | Some(con) -> con
        end;

    const callback : operation = Tezos.transaction(
        (event.currencyPair, entrypoint),
        0tez,
        callToOracle);
} with list[callback]
