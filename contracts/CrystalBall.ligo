type callbackReturnedValue is record [
    currencyPair : string;
    lastUpdate : timestamp;
    rate : nat
]

type callbackReturnedValueMichelson is michelson_pair_right_comb(callbackReturnedValue)

type callbackEntrypoint is contract(callbackReturnedValueMichelson)

type oracleParam is string * contract(callbackReturnedValueMichelson)

type eventIdType is option(nat)

type betType is
| For of unit
| Against of unit

type betParams is record [
    eventId : eventIdType;
    bet : betType;
    minimalWinAmount : tez;
]

type ledgerKey is (address*eventIdType)

(* ledger key is address and event ID *)
type ledgerType is big_map(ledgerKey, tez)


type eventType is record [
    currencyPair : string;
    createdTime : timestamp;

    (* targetDynamics is natural number in grades of targetDynamicsPrecision
        more than targetDynamicsPrecision means price is increased,
        less targetDynamicsPrecision mean price is decreased *)
    targetDynamics : nat;
    targetDynamicsPrecision : nat;

    (* time since new bets would not be accepted *)
    betsCloseTime : timestamp;

    (* time that setted when recieved callback from startMeasurement *)
    measureOracleStartTime : timestamp;
    isMeasurementStarted : bool;

    (* the rate at the begining of the measurement *)
    startRate : nat;

    (* measurePeriod is amount of seconds from measureStartTime before 
        anyone can call close tp finish event *)
    measurePeriod : nat;

    isClosed : bool;
    closedOracleTime : timestamp;

    (* keeping closedRate for debugging purposes, it can be deleted after *)
    closedRate : nat;
    closedDynamics : nat;
    isBetsForWin : bool;

    oracleAddress : address;

    betsForSum : tez;
    betsAgainstSum : tez;

    (* withdrawnSum is sum that was withdrawn by participant, needed to calculate
        sum thatcan withdraw liquidity provider *)
    withdrawnSum : tez;

    (* Liquidity provider bonus: numerator & denominator *)
    liquidityPercent : nat;
    liquidityPrecision : nat;

    (* Fees, that should be provided during contract origination *)
    measureStartFee : tez;
    expirationFee : tez;

    (* Fees, that taken from participants *)
    rewardCallFee : tez;

    (* Participants count, provider can withdraw liquidity only when participants is 0 *)
    participants : nat;
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
    betFor : tez;
    betAgainst : tez;
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
    lastEventId : eventIdType;
    closeCallEventId : eventIdType;
    measurementStartCallEventId : eventIdType;
]


function newEvent(var eventParams : newEventParams; var s : storage) : storage is
block {
    (* TODO: assert that betFor + betAgainst is equal to Tezos.amount *)
    (* TODO: assert that betFor / betAgainst is less than MAX_RATIO controlled by Manager *)
    (* TODO: assert that betAgainst / betFor is less than MAX_RATIO controlled by Manager *)
    (* TODO: assert that Tezos.amount is more than MIN_LIQUIDITY controlled be Manager *)
    (* TODO: decide, should newEvent creator provide liquidity or not? maybe it is not important? *)
    (* TODO: Checking that betsCloseTime of this event is in the future: *)
    (* TODO: Checking that measurePeriod is more than some minimal amount and maybe less than amount *)
    (* TODO: Check that liquidityPercent is less than 1_000_000 *)
    (* TODO: Check that measureStartFee and expirationFee is equal to Tezos.amount *)

    const newEvent : eventType = record[
        currencyPair = eventParams.currencyPair;
        createdTime = Tezos.now;
        targetDynamics = eventParams.targetDynamics;
        targetDynamicsPrecision = 1_000_000n;
        betsCloseTime = eventParams.betsCloseTime;
        measureOracleStartTime = ("2018-06-30T07:07:32Z" : timestamp);
        isMeasurementStarted = False;
        startRate = 0n;
        (* TODO: control measurePeriod, time to betsCloseTime min|max from Manager *)
        measurePeriod = eventParams.measurePeriod;
        isClosed = False;
        closedOracleTime = ("2018-06-30T07:07:32Z" : timestamp);
        closedRate = 0n;
        closedDynamics = 0n;
        isBetsForWin = False;
        oracleAddress = eventParams.oracleAddress;
        betsForSum = eventParams.betFor;
        betsAgainstSum = eventParams.betAgainst;
        (* TODO: control liquidityPrecision, liquidityPercent min|max from Manager *)
        liquidityPercent = eventParams.liquidityPercent;
        liquidityPrecision = 1_000_000n;
        measureStartFee = eventParams.measureStartFee;
        expirationFee = eventParams.expirationFee;
        (* TODO: control rewardCallFee from Manager *)
        rewardCallFee = 100_000mutez;
        participants = 0n;
        withdrawnSum = 0tez;
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

(* Returns minimal value from two nat variables a & b *)
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


function bet(var p : betParams; var s : storage) : storage is
block {
    
    // const betFor : tez = p.betFor;
    // const betAgainst : tez = p.betAgainst;
    const eventId : eventIdType = p.eventId;
    const event : eventType = getEvent(s, eventId);

    if (Tezos.now > event.betsCloseTime) then
        failwith("Bets after betCloseTime is not allowed")
    else skip;

    (*if (betFor + betAgainst) =/= Tezos.amount then
        failwith("Sum of bets is not equal to send amount")
    else skip;*)

    if event.isClosed then failwith("Event already closed") else skip;

    (*
    const elapsedTime : int = Tezos.now - event.createdTime;
    if (elapsedTime < 0) then
        failwith("Bet adding before contract createdTime (possible wrong createdTime?)")
    else skip;
    *)

    (* TODO: assert that Tezos.amount is more than zero? (instead it can lead to junk records
        in ledgers, that would not be removed) *)
    const key : ledgerKey = (Tezos.sender, eventId);

    const alreadyBetValue : tez =
        getLedgerAmount(key, s.betsForLedger) + getLedgerAmount(key, s.betsAgainstLedger);

    if (alreadyBetValue = 0tez) then
        event.participants := event.participants + 1n;
    else skip;

    case p.bet of
    | For -> block {
        event.betsForSum := event.betsForSum + Tezos.amount;
        const possibleWinAmount : tez = (
            Tezos.amount + Tezos.amount / 1mutez * event.betsAgainstSum / event.betsForSum * 1mutez);
        (* TODO: check that amount is more than p.minimalWinAmount *)
        s.betsForLedger[key] := getLedgerAmount(key, s.betsForLedger) + possibleWinAmount;
    }
    | Against -> {
        event.betsAgainstSum := event.betsAgainstSum + Tezos.amount;
        const possibleWinAmount : tez = (
            Tezos.amount + Tezos.amount / 1mutez * event.betsForSum / event.betsAgainstSum * 1mutez);
        (* TODO: check that amount is more than p.minimalWinAmount *)
        s.betsAgainstLedger[key] := getLedgerAmount(key, s.betsAgainstLedger) + possibleWinAmount;
    }
    end;

    s.events[eventId] := event;
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
    (* When calling close event, s.closeCallEventId should be equal to None, otherwise
        it looks like another callback is runned but no answer is received yet (is it
        even possible, btw?) *)
    case s.closeCallEventId of
    | Some(closeCallEventId) -> failwith("Another call to oracle in process (should not be here)")
    | None -> skip
    end;

    const operations = makeCallToOracle(
        eventId, s, (Tezos.self("%closeCallback") : callbackEntrypoint));
    s.closeCallEventId := eventId;

} with (operations, s)


function startMeasurement(var eventId : eventIdType; var s : storage) : (list(operation) * storage) is
block {
    case s.measurementStartCallEventId of
    | Some(measurementStartCallEventId) -> failwith("Another call to oracle in process (should not be here)")
    | None -> skip
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

    (* TODO: Check that current time is not far away from betsCloseTime, if it is,
        run Force Majeure. Give Manager ability to control this timedelta *)
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
    event.isMeasurementStarted := True;

    // Paying measureStartFee for this method initiator:
    const receiver : contract(unit) = getReceiver(Tezos.source);
    // TODO: somehow check that s.measureStartFee is provided (maybe I need init method that requires
    // to be supported with measureStartFee + liquidationFee?)
    const payoutOperation : operation = Tezos.transaction(unit, event.measureStartFee, receiver);

    s.events[eventId] := event;

    // Cleaning up event ID:
    s.measurementStartCallEventId := (None : eventIdType);

} with (list[payoutOperation], s)


function closeCallback(
    var p : callbackReturnedValueMichelson;
    var s : storage) : (list(operation) * storage) is
block {

    const eventId : eventIdType = s.closeCallEventId;

    (* TODO: Check that current time is not far away from measurementStartTime + timedelta,
        if it is, run Force Majeure. Give Manager ability to control this timedelta *)

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

    const endTime : timestamp = event.measureOracleStartTime + int(event.measurePeriod);
    if param.lastUpdate < endTime then
        failwith("Can't close until lastUpdate reached measureStartTime + measurePeriod") else skip;
    (* TODO: what should be done if time is very late? (i.e. cancel event and allow withdrawals?) *)
    if event.isClosed then failwith("Contract already closed. Can't close contract twice") else skip;

    // Closing contract:
    event.closedOracleTime := param.lastUpdate;
    event.closedRate := param.rate;
    event.closedDynamics := param.rate * 1000000n / event.startRate;
    event.isClosed := True;
    event.isBetsForWin := event.closedDynamics > event.targetDynamics;

    (* TODO: what should be done if all bets were For and all of them are loose?
        All raised funds will be freezed. Should they all be winners anyway? *)

    // Paying expirationFee for this method initiator:
    const receiver : contract(unit) = getReceiver(Tezos.source);
    // TODO: AGAIN: somehow check that s.expirationFee is provided (maybe I need init method
    // that requires to be supported with measureStartFee + liquidationFee?)
    const expirationFeeOperation : operation = Tezos.transaction(unit, event.expirationFee, receiver);

    s.events[eventId] := event;

    // Cleaning up event ID:
    s.closeCallEventId := (None : eventIdType);

} with (list[expirationFeeOperation], s)


function withdraw(var eventId : eventIdType; var s: storage) : (list(operation) * storage) is
block {
    (* TODO: add list of reciever addresses to make bulk transactions
        and make it possible to call it by anyone *)
    const event : eventType = getEvent(s, eventId);
    const key : ledgerKey = (Tezos.sender, eventId);

    // Checks that this method can be runned:
    if event.isClosed then skip
    else failwith("Withdraw is not allowed until contract is closed");

    const payoutAmount : tez = (
        getLedgerAmount(key, s.betsForLedger)
        + getLedgerAmount(key, s.betsAgainstLedger));

    // Getting reciever:
    const receiver : contract(unit) = getReceiver(Tezos.sender);

    // Removing sender from all ledgers:
    s.betsForLedger := Big_map.remove(key, s.betsForLedger);
    s.betsAgainstLedger := Big_map.remove(key, s.betsAgainstLedger);
    event.withdrawnSum := event.withdrawnSum + payoutAmount;

    event.participants := abs(event.participants - 1n);

    if (payoutAmount = 0tez) then failwith("Nothing to withdraw") else skip;

    const payoutOperation : operation = Tezos.transaction(unit, payoutAmount, receiver);

    s.events[eventId] := event;

} with (list[payoutOperation], s)


(* TODO: method to withdraw for liquidity provider:
    event.betsForSum + event.betsAgainstSum - event.withdrawnSum
 *)

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
