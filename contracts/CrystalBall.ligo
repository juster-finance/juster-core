type callbackReturnedValue is record [
    currencyPair : string;
    lastUpdate : timestamp;
    rate : nat
]

type callbackReturnedValueMichelson is michelson_pair_right_comb(callbackReturnedValue)

type oracleParam is string * contract(callbackReturnedValueMichelson)


type action is
| BetFor of unit
| BetAgainst of unit
| Close of unit
| CloseCallback of callbackReturnedValueMichelson
| Withdraw of unit
(* TODO: reopen with new state? (no, I feel that it is better keep it simple) *)


type storage is record [
    currencyPair : string;
    targetRate : nat;
    targetTime : timestamp;
    (* TODO: maybe it should be one ledger with record that contains bet type? *)
    betsForLedger : big_map(address, tez);
    betsAgainstLedger : big_map(address, tez);
    oracleAddress : address;
    // adminAddress : address;
    isClosed : bool;
    closedTime : timestamp;
    closedRate : nat;
    betsForSum : nat;
    betsAgainstSum : nat;
    isBetsForWin : bool;
]


function betFor(var s : storage) : storage is
block {
    (* TODO: check that current time is less than targetTime somehow? *)

    if s.isClosed then failwith("Contract already closed") else skip;

    (* TODO: check if this sender already in ledger, if it is add Tezos.amount
        to already existing bets. Now it is just disallowed to make another bet to same ledger: *)
    case Big_map.find_opt(Tezos.sender, s.betsForLedger) of
    | Some(acc) -> failwith("Account already made betFor")
    | None -> s.betsForLedger[Tezos.sender] := Tezos.amount
    end

} with s


function betAgainst(var s : storage) : storage is
block {

    if s.isClosed then failwith("Contract already closed") else skip;

    (* TODO: check if this sender already in ledger, if it is add Tezos.amount
        to already existing bets. Now it is just disallowed to make another bet to same ledger: *)
    case Big_map.find_opt(Tezos.sender, s.betsAgainstLedger) of
    | Some acc -> failwith("Account already made betAgainst")
    | None -> s.betsAgainstLedger[Tezos.sender] := Tezos.amount
    end
    
} with s


function close(var s : storage) : list(operation) is
block {

    const callToOracle : contract(oracleParam) =
        case (Tezos.get_entrypoint_opt("%get", s.oracleAddress) : option(contract(oracleParam))) of
        | None -> (failwith("No oracle found") : contract(oracleParam))
        | Some(con) -> con
        end;

    const callback : operation = Tezos.transaction(
        (s.currencyPair, (Tezos.self("%closeCallback") : contract(callbackReturnedValueMichelson))),
        0tez,
        callToOracle);

} with list[callback]


function closeCallback(var p : callbackReturnedValueMichelson; var s : storage) : storage is
block {
    // Check that callback runs from right address and with right currency pair:
    if Tezos.sender =/= s.oracleAddress then (failwith("Unknown sender") : storage)
    else skip;

    if p.currencyPair =/= s.currencyPair then (failwith("Unexpected currency pair"): storage)
    else skip;

    if p.targetTime > s.lastUpdate then (failwith("Can't close until reached targetTime"): storage)
    else skip;

    if s.isClosed then (failwith("Contract already closed. Can't close contract twice"): storage)
    else skip;

    // Closing contract:
    const param : callbackReturnedValue = Layout.convert_from_right_comb(p);
    s.closedTime := param.lastUpdate;
    s.closedRate := param.rate;
    s.isClosed := True;
    s.isBetsForWin := param.rate > s.targetRate;

    (* TODO: what should be done if all bets were For and all of them are loose?
        All raised funds will be freezed. Should they all be winners anyway? *)

} with s


(* TODO: would it be better if it would make all withdraw operations inside closeCallback? *)
function withdraw(var s: storage) : (list(operation) * storage) is
block {

    // Checks that this method can be runned:
    if s.isClosed then skip
    else failwith("Withdraw is not allowed until contract is closed");

    // Calculating payoutAmount:
    const winBetsSum : if s.isBetsForWin then s.betsForSum else s.betsAgainstSum;
    const winLedger : if s.isBetsForWin then s.betsForLedger else s.betsAgainstLedger;

    const participantSum : tez =
        case winLedger[Tezos.sender] of
        | Some (val) -> val
        | None -> (failwith("Participant is not win") : tez)

    const totalBets : nat = s.betsForSum + s.betsAgainstSum;
    const payoutAmount : tez = participantSum / winBetsSum * totalBets;

    // Getting reciever:
    const receiver : contract(unit) =
        case (Tezos.get_contract_opt(Tezos.sender): option(contract(unit))) of
        | Some (con) -> con
        | None -> (failwith ("Not a contract") : (contract(unit)))
        end;

    // Removing sender from ledger:
    const updatedLedger = Big_map.remove(Tezos.sender, winLedger);
    if s.isBetsForWin then block {
        s.betsForLedger := updatedLedger
    }
    else s.betsAgainstLedger := updatedLedger;

    const payoutOperation : operation = Tezos.transaction(unit, payoutAmount, receiver);

} with list[payoutOperation], s


function main (var params : action; var s : storage) : (list(operation) * storage) is
case params of
| BetFor -> ((nil: list(operation)), betFor(s))
| BetAgainst -> ((nil: list(operation)), betAgainst(s))
| Close -> (close(s), s)
| CloseCallback(p) -> ((nil: list(operation)), closeCallback(p, s))
| Withdraw -> withdraw(s)
end
