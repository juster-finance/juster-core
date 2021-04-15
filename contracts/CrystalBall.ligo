type callbackReturnedValue is record [
    currencyPair : string;
    lastUpdate : timestamp;
    rate : nat
]

type callbackReturnedValueMichelson is michelson_pair_right_comb(callbackReturnedValue)

type callbackEntrypoint is contract(callbackReturnedValueMichelson)

type oracleParam is string * contract(callbackReturnedValueMichelson)

type eventIdType is option(nat)

type betParams is record [
    eventId : eventIdType;
    betFor : tez;
    betAgainst : tez;
]

type ledgerKey is (address*eventIdType)

(* ledger key is address and event ID *)
type ledgerType is big_map(ledgerKey, tez)

// THIS STORAGE SHOULD BE IN MAP/BIGMAP (each event should have this storage)
// All ledgers (betsForLedger, betsAgainstLedger and liquidityLedger) should be
// in three BigMaps with structured key (eventId + address)
type eventType is record [
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

    // measureStartTime is a time, after betsClosedTime, that setted when someone calls
    // startMeasurement
    measureStartTime : timestamp;
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

    oracleAddress : address;

    betsForSum : tez;
    betsAgainstSum : tez;
    liquiditySum : tez;

    liquidityPercent : nat;  // natural number from 0 to 1_000_000 that represent share

    // TODO: Fees should be provided during contract origination!
    measureStartFee : tez;
    expirationFee : tez;
]


type newEventParams is record [
    currencyPair : string;
    targetDynamics : nat;
    betsCloseTime : timestamp;
    measurePeriod : nat;
    oracleAddress :  address;
    liquidityPercent : nat;
    measureStartFee : tez;
    expirationFee : tez;
]


type action is
| NewEvent of newEventParams
| Bet of betParams
| StartMeasurement of eventIdType
| StartMeasurementCallback of callbackReturnedValueMichelson
| Close of eventIdType
| CloseCallback of callbackReturnedValueMichelson
| Withdraw of eventIdType


type storage is record [
    events : big_map(eventIdType, eventType);
    betsForLedger : ledgerType;
    betsAgainstLedger : ledgerType;
    liquidityLedger : ledgerType;
    lastEventId : eventIdType;
    closeCallEventId : eventIdType;
    measurementStartCallEventId : eventIdType;
]


function newEvent(var eventParams : newEventParams; var s : storage) : storage is
block {
    (* TODO: decide, should newEvent creator provide liquidity or not? maybe it is not important? *)
    (* TODO: Checking that betsCloseTime of this event is in the future: *)
    (* TODO: Checking that measurePeriod is more than some minimal amount and maybe less than amount *)
    (* TODO: Check that liquidityPercent is less than 1_000_000 *)
    (* TODO: Check that measureStartFee and expirationFee is equal to Tezos.amount *)

    const newEvent : eventType = record[
        currencyPair = eventParams.currencyPair;
        createdTime = Tezos.now;
        targetDynamics = eventParams.targetDynamics;
        betsCloseTime = eventParams.betsCloseTime;
        measureStartTime = ("2018-06-30T07:07:32Z" : timestamp);
        measureOracleStartTime = ("2018-06-30T07:07:32Z" : timestamp);
        isMeasurementStarted = False;
        startRate = 0n;
        measurePeriod = 0n;
        isClosed = False;
        closedTime = ("2018-06-30T07:07:32Z" : timestamp);
        closedOracleTime = ("2018-06-30T07:07:32Z" : timestamp);
        closedRate = 0n;
        closedDynamics = 0n;
        isBetsForWin = False;
        oracleAddress = eventParams.oracleAddress;
        betsForSum = 0tez;
        betsAgainstSum = 0tez;
        liquiditySum = 0tez;
        liquidityPercent = eventParams.liquidityPercent;
        measureStartFee = eventParams.measureStartFee;
        expirationFee = eventParams.expirationFee;
    ];

    s.events[s.lastEventId] := newEvent;

    (* NOTE: This is strange construction, but I do not understand how to
        assign value to option(nat) variable, maybe it should be changed *)
    case s.lastEventId of
    | Some(eventId) -> s.lastEventId := Some(eventId + 1n)
    | None -> failwith("s.lastEventId is None, should not be here")
    end;
} with s


(* Returns current amount of tez in ledger, if key is not in ledger return 0tez *)
function getLedgerAmount(var k : ledgerKey; var l : ledgerType) : tez is
block {
    var ledgerAmount : tez := 0tez;
    case Big_map.find_opt(k, l) of
    | Some(value) -> ledgerAmount := value
    | None -> ledgerAmount := 0tez
    end;
} with ledgerAmount


function minNat(var a : nat; var b : nat) : nat is
block {
    var minValue : nat := a;
    if (a > b) then minValue := b else skip;
} with minValue


function tezToNat(var t : tez) : nat is t / 1mutez;


function getEvent(var s : storage; var eventId : eventIdType) : eventType is
case Big_map.find_opt(eventId, s.events) of
| Some(event) -> event
| None -> (failwith("Event is not found") : eventType)
end;


// TODO: need to figure out how to create method with params:
function bet(var p : betParams; var s : storage) : storage is
block {
    const betFor : tez = p.betFor;
    const betAgainst : tez = p.betAgainst;
    const eventId : eventIdType = p.eventId;
    const event : eventType = getEvent(s, eventId);

    if (Tezos.now > event.betsCloseTime) then
        failwith("Bets after betCloseTime is not allowed")
    else skip;

    if (betFor + betAgainst) =/= Tezos.amount then
        failwith("Sum of bets is not equal to send amount")
    else skip;

    if event.isClosed then failwith("Event already closed") else skip;

    const elapsedTime : int = Tezos.now - event.createdTime;
    if (elapsedTime < 0) then
        failwith("Bet adding before contract createdTime (possible wrong createdTime?)")
    else skip;

    const key : ledgerKey = (Tezos.sender, eventId);

    if (betFor > 0tez) then {
        const newAmount : tez = getLedgerAmount(key, s.betsForLedger) + betFor;
        s.betsForLedger[key] := newAmount;
        event.betsForSum := event.betsForSum + betFor;
    } else skip;

    if (betAgainst > 0tez) then {
        const newAmount : tez = getLedgerAmount(key, s.betsAgainstLedger) + betAgainst;
        s.betsAgainstLedger[key] := newAmount;
        event.betsAgainstSum := event.betsAgainstSum + betAgainst;
    } else skip;

    (* Adding liquidity bonus:
        Liquidity represent added value, that goes both to betFor and betAgainst pools.
        Liquidity is important at the begining of the event and useless at the end. To evaluate
        liquidity bonus, contract calculates remained time (seconds till betsCloseTime) and used
        it as a linear multiplicator for minimal amount between betAgainst and betFor
     *)
    if (betAgainst > 0tez) and (betFor > 0tez) then {
        // TODO: s.betsCloseTime SHOULD be more than s.createdTime, need to have check in contract creation
        const totalBettingTime : nat = abs(event.betsCloseTime - event.createdTime);
        const remainedTime : int = totalBettingTime - elapsedTime;

        const addedLiquidity : nat = minNat(tezToNat(betAgainst), tezToNat(betFor));
        const liquidityBonus : tez = abs(remainedTime) * addedLiquidity * 1mutez / totalBettingTime;

        const newAmount : tez = getLedgerAmount(key, s.liquidityLedger) + liquidityBonus;
        s.liquidityLedger[key] := newAmount;
        event.liquiditySum := event.liquiditySum + liquidityBonus;
    } else skip;
} with s


function makeCallToOracle(
    var eventId : eventIdType;
    var s : storage;
    var entrypoint : callbackEntrypoint) : list(operation) is
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


function close(var eventId : eventIdType; var s : storage) : (list(operation) * storage) is
block {
    case s.closeCallEventId of
    | Some(closeCallEventId) -> skip
    | None -> failwith("Another call to oracle in process (should not be here)")
    end;

    const operations = makeCallToOracle(
        eventId, s, (Tezos.self("%closeCallback") : callbackEntrypoint));
    s.closeCallEventId := eventId;

} with (operations, s)


function startMeasurement(var eventId : eventIdType; var s : storage) : (list(operation) * storage) is
block {
    case s.measurementStartCallEventId of
    | Some(measurementStartCallEventId) -> skip
    | None -> failwith("Another call to oracle in process (should not be here)")
    end;

    const operations = makeCallToOracle(
        eventId, s, (Tezos.self("%startMeasurementCallback") : callbackEntrypoint));
    s.measurementStartCallEventId := eventId;

} with (operations, s)


function getReceiver(var a : address) : contract(unit) is
    case (Tezos.get_contract_opt(a): option(contract(unit))) of
    | Some (con) -> con
    | None -> (failwith ("Not a contract") : (contract(unit)))
    end;


function startMeasurementCallback(
    var p : callbackReturnedValueMichelson;
    var s : storage) : (list(operation) * storage) is
block {
    const param : callbackReturnedValue = Layout.convert_from_right_comb(p);

    const eventId : eventIdType = s.measurementStartCallEventId;

    case eventId of
    | Some(measurementStartCallEventId) -> skip
    | None -> failwith("measurementStartCallEventId is empty")
    end;

    const event : eventType = getEvent(s, eventId);

    // Check that callback runs from right address and with right currency pair:
    if Tezos.sender =/= event.oracleAddress then failwith("Unknown sender") else skip;
    if param.currencyPair =/= event.currencyPair then failwith("Unexpected currency pair") else skip;
    if event.isMeasurementStarted then failwith("Measurement period already started") else skip;
    if event.betsCloseTime > param.lastUpdate then
        failwith("Can't start measurement untill betsCloseTime (maybe oracle have outdated info?)") else skip;
    (* TODO: what should be done if time is very late? (i.e. cancel event and allow withdrawals?) *)

    // Starting measurement:
    event.measureOracleStartTime := param.lastUpdate;
    event.startRate := param.rate;
    event.measureStartTime := Tezos.now;
    event.isMeasurementStarted := True;

    // Paying measureStartFee for this method initiator:
    const receiver : contract(unit) = getReceiver(Tezos.source);
    // TODO: somehow check that s.measureStartFee is provided (maybe I need init method that requires
    // to be supported with measureStartFee + liquidationFee?)
    const payoutOperation : operation = Tezos.transaction(unit, event.measureStartFee, receiver);

    // Cleaning up event ID:
    s.measurementStartCallEventId := (None : eventIdType);

} with (list[payoutOperation], s)


function closeCallback(
    var p : callbackReturnedValueMichelson;
    var s : storage) : (list(operation) * storage) is
block {

    const eventId : eventIdType = s.closeCallEventId;

    case eventId of
    | Some(closeCallEventId) -> skip
    | None -> failwith("closeCallEventId is empty")
    end;

    const param : callbackReturnedValue = Layout.convert_from_right_comb(p);

    const event : eventType = getEvent(s, eventId);

    // Check that callback runs from right address and with right currency pair:
    if Tezos.sender =/= event.oracleAddress then failwith("Unknown sender") else skip;
    if param.currencyPair =/= event.currencyPair then failwith("Unexpected currency pair") else skip;

    if not event.isMeasurementStarted then
        failwith("Can't close contract before measurement period started")
    else skip;

    const endTime : timestamp = event.measureStartTime + int(event.measurePeriod);
    if endTime < param.lastUpdate then
        failwith("Can't close until lastUpdate reached measureStartTime + measurePeriod") else skip;
    (* TODO: what should be done if time is very late? (i.e. cancel event and allow withdrawals?) *)
    if event.isClosed then failwith("Contract already closed. Can't close contract twice") else skip;

    // Closing contract:
    event.closedOracleTime := param.lastUpdate;
    event.closedRate := param.rate;
    event.closedDynamics := param.rate * 1000000n / event.startRate;
    event.closedTime := Tezos.now;
    event.isClosed := True;
    event.isBetsForWin := event.closedDynamics > event.targetDynamics;

    (* TODO: what should be done if all bets were For and all of them are loose?
        All raised funds will be freezed. Should they all be winners anyway? *)

    // Paying expirationFee for this method initiator:
    const receiver : contract(unit) = getReceiver(Tezos.source);
    // TODO: AGAIN: somehow check that s.expirationFee is provided (maybe I need init method
    // that requires to be supported with measureStartFee + liquidationFee?)
    const expirationFeeOperation : operation = Tezos.transaction(unit, event.expirationFee, receiver);

    // Cleaning up event ID:
    s.closeCallEventId := (None : eventIdType);

} with (list[expirationFeeOperation], s)


function withdraw(var eventId : eventIdType; var s: storage) : (list(operation) * storage) is
block {

    const event : eventType = getEvent(s, eventId);
    const key : ledgerKey = (Tezos.sender, eventId);

    // Checks that this method can be runned:
    if event.isClosed then skip
    else failwith("Withdraw is not allowed until contract is closed");

    // Calculating payoutAmount:
    const winBetsSum : tez =
        if event.isBetsForWin then event.betsForSum else event.betsAgainstSum;
    const winLedger : ledgerType =
        if event.isBetsForWin then s.betsForLedger else s.betsAgainstLedger;

    const participantSum : tez = getLedgerAmount(key, winLedger);
    const participantLiquidity : tez = getLedgerAmount(key, s.liquidityLedger);

    const totalBets : tez = event.betsForSum + event.betsAgainstSum;
    const totalWinPayoutAmount : tez = totalBets * abs (1_000_000n - event.liquidityPercent) / 1_000_000n;
    const totalLiquidityBonus : tez = totalBets * event.liquidityPercent / 1_000_000n;

    const winPayoutAmount : tez = (
        participantSum / 1mutez * totalWinPayoutAmount / winBetsSum * 1mutez);
    const liquidityBonusAmount : tez = (
        participantLiquidity / 1mutez * totalLiquidityBonus / event.liquiditySum * 1mutez);

    const payoutAmount : tez = winPayoutAmount + liquidityBonusAmount;

    // Getting reciever:
    const receiver : contract(unit) = getReceiver(Tezos.sender);

    // Removing sender from wins ledger:
    const updatedLedger = Big_map.remove(key, winLedger);
    if event.isBetsForWin then
        s.betsForLedger := updatedLedger
    else s.betsAgainstLedger := updatedLedger;

    // Removing sender from liquidity ledger:
    s.liquidityLedger := Big_map.remove(key, s.liquidityLedger);

    if (payoutAmount = 0tez) then failwith("Nothing to withdraw") else skip;

    const payoutOperation : operation = Tezos.transaction(unit, payoutAmount, receiver);

} with (list[payoutOperation], s)


function main (var params : action; var s : storage) : (list(operation) * storage) is
case params of
| NewEvent(p) -> ((nil: list(operation)), newEvent(p, s))
| Bet(p) -> ((nil: list(operation)), bet(p, s))
| StartMeasurement(p) -> (startMeasurement(p, s))
| StartMeasurementCallback(p) -> (startMeasurementCallback(p, s))
| Close(p) -> (close(p, s))
| CloseCallback(p) -> (closeCallback(p, s))
| Withdraw(p) -> withdraw(p, s)
end

(* TODO: should it be some kind of destroy event method? or it is not important? *)
