type callbackReturnedValue is record [
    currencyPair : string;
    lastUpdate : timestamp;
    rate : nat
]

type callbackReturnedValueMichelson is michelson_pair_right_comb(callbackReturnedValue)

type oracleParam is string * contract(callbackReturnedValueMichelson)

type betParams is record [
    betFor : tez;
    betAgainst : tez;
]

type action is
| Bet of betParams
| StartMeasurement of unit
| StartMeasurementCallback of callbackReturnedValueMichelson
| Close of unit
| CloseCallback of callbackReturnedValueMichelson
| Withdraw of unit
(* TODO: reopen with new state? (no, I feel that it is better keep it simple) *)


type ledger is big_map(address, tez);


// THIS STORAGE SHOULD BE IN MAP/BIGMAP (each event should have this storage)
// All ledgers (betsForLedger, betsAgainstLedger and liquidityLedger) should be
// in three BigMaps with structured key (eventId + address)
type storage is record [
    currencyPair : string;

    // createdTime is time when contract created, used to ajust liquidity bonus:
    createdTime : timestamp;

    // targetDynamics is natural number in grades of 1_000_000, more than 1kk mean
    // price is increased, less 1kk mean price is decreased;
    // if targetDynamics === 1_000_000 -- it means betsFor are bets for any increase
    // and betsAgainst is bets for any decrese:
    targetDynamics : nat;

    // betsCloseTime is time when no new bets accepted:
    betsCloseTime : timestamp;
    // TODO: need to decide, if betsCloseTime equal to measureStartTime or it is needed
    // to add another time instance?

    // measuseStartTime is a time, after betsClosedTime, that setted when someone calls
    // startMeasurement
    measuseStartTime : timestamp;
    // this is time from oracle call, need to decide what time is better to keep:
    measureOracleStartTime : timestamp;
    isMeasurementStarted : bool;

    // startRate: the rate at the begining of the measurement:
    startRate : nat;

    // measurePeriod is amount of seconds from measureStartTime before 
    // after this period elapsed, anyone can run close() and measure dynamics:
    measurePeriod : nat;

    isClosed : bool;
    closedTime : timestamp;
    // the same with closedTime, alternative is closedOracleTime:
    closedOracleTime : timestamp;

    // keeping closedRate for debugging purposes, it can be deleted after:
    closedRate : nat;
    closedDynamics : nat;
    isBetsForWin : bool;

    (* TODO: maybe it should be one ledger with record that contains bet type? *)
    betsForLedger : ledger;
    betsAgainstLedger : ledger;
    liquidityLedger : ledger;

    oracleAddress : address;

    betsForSum : tez;
    betsAgainstSum : tez;
    liquiditySum : tez;

    liquidityPercent : nat;  // natural number from 0 to 1_000_000 that represent share
    expirationFee : tez;
]

(* Returns current amount of tez in ledger, if key is not in ledger return 0tez *)
function getLedgerAmount(var k : address; var l : ledger) : tez is
block {
    var ledgerAmount : tez := 0tez;
    case Big_map.find_opt(k, l) of
    | Some(value) -> ledgerAmount := value
    | None -> ledgerAmount := 0tez
    end;
} with ledgerAmount


// TODO: need to figure out how to create method with params:
function bet(var p : betParams; var s : storage) : storage is
block {
    const betFor : tez = p.betFor;
    const betAgainst : tez = p.betAgainst;
    (* TODO: check that current time is less than betsCloseTime *)
    if (betFor + betAgainst) =/= Tezos.amount then
        failwith("Sum of bets is not equal to send amount")
    else skip;

    if s.isClosed then failwith("Contract already closed") else skip;

    if (betFor > 0tez) then {
        const newAmount : tez = getLedgerAmount(Tezos.sender, s.betsForLedger) + betFor;
        s.betsForLedger[Tezos.sender] := newAmount;
        s.betsForSum := s.betsForSum + betFor;
    } else skip;

    if (betAgainst > 0tez) then {
        const newAmount : tez = getLedgerAmount(Tezos.sender, s.betsAgainstLedger) + betAgainst;
        s.betsAgainstLedger[Tezos.sender] := newAmount;
        s.betsAgainstSum := s.betsAgainstSum + betAgainst;
    } else skip;

    // TODO MUST: add liquidity bonus as minimal from betFor and betAgainst 
    if (betAgainst > 0tez) and (betFor > 0tez) then {
        // const liquidityBonus = Tezos.now
        // TODO: calculate liquidity bonus as minimal from betAgainst & betFor
        // and multiply it by time difference Tezos.now - s.createdTime
        const elapsedTime = Tezos.now - s.createdTime;
        // TODO MUST: instead of abs(elapsedTime) need to return Max(0, elapsedTime)?
        s.liquidityLedger[Tezos.sender] := abs(elapsedTime) * 1mutez;
        // TODO MUST: instead time write time difference as constant in mutez
        // TODO: remember to add this to s.liquiditySum
    } else skip;
} with s


function startMeasurement(var s : storage) : list(operation) is
block {
    const operations : list(operation) = nil;
} with operations // TODO: list[callback]


function startMeasurementCallback(var p : callbackReturnedValueMichelson; var s : storage) : storage is
block {skip} with s


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
    const param : callbackReturnedValue = Layout.convert_from_right_comb(p);

    // Check that callback runs from right address and with right currency pair:
    if Tezos.sender =/= s.oracleAddress then failwith("Unknown sender") else skip;
    if param.currencyPair =/= s.currencyPair then failwith("Unexpected currency pair") else skip;
    const endTime : timestamp = s.measuseStartTime + int(s.measurePeriod);
    if endTime > param.lastUpdate then
        failwith("Can't close until lastUpdate reached measuseStartTime + measurePeriod") else skip;
    if s.isClosed then failwith("Contract already closed. Can't close contract twice") else skip;

    // Closing contract:
    s.closedOracleTime := param.lastUpdate;
    s.closedRate := param.rate;
    s.closedDynamics := param.rate * 1000000n / s.startRate;
    s.closedTime := Tezos.now;
    s.isClosed := True;
    s.isBetsForWin := s.closedDynamics > s.targetDynamics;

    // TODO: change this method to measure difference between currency rate
    // !!! TODO: who would call oracle when measureStartTime / betsCloseTime starts?

    // TODO: calculate luqidity bonus and expirationFee
    // TODO: make all transactions inside closeCallback instead of calling withdraws?

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
    const winBetsSum : tez =
        if s.isBetsForWin then s.betsForSum else s.betsAgainstSum;
    const winLedger : big_map(address, tez) =
        if s.isBetsForWin then s.betsForLedger else s.betsAgainstLedger;

    const participantSum : tez =
        case winLedger[Tezos.sender] of
        | Some (val) -> val
        | None -> (failwith("Participant is not win") : tez)
        end;

    const totalBets : tez = s.betsForSum + s.betsAgainstSum;
    const payoutAmount : tez = participantSum / 1mutez * totalBets / winBetsSum * 1mutez;

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

} with (list[payoutOperation], s)


function main (var params : action; var s : storage) : (list(operation) * storage) is
case params of
| Bet(p) -> ((nil: list(operation)), bet(p, s))
| StartMeasurement -> (startMeasurement(s), s)
| StartMeasurementCallback(p) -> ((nil: list(operation)), startMeasurementCallback(p, s))
| Close -> (close(s), s)
| CloseCallback(p) -> ((nil: list(operation)), closeCallback(p, s))
| Withdraw -> withdraw(s)
end
