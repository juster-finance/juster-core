function closeCallback(
    const param : callbackReturnedValue;
    var store : storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    const eventId : nat = case store.closeCallId of [
    | Some(closeCallId) -> closeCallId
    | None -> (failwith("closeCallId is empty") : nat)
    ];

    var event : eventType := getEvent(store, eventId);

    (* Check that callback runs from right address
        and with right currency pair: *)
    if Tezos.get_sender() =/= event.oracleAddress
    then failwith("Unknown sender") else skip;
    if param.currencyPair =/= event.currencyPair
    then failwith("Unexpected currency pair") else skip;

    const startedTime : timestamp = case event.measureOracleStartTime of [
    | Some(t) -> t
    | None -> (failwith("Can't close event before measurement period started") : timestamp)
    ];

    const endTime : timestamp = startedTime + int(event.measurePeriod);
    if param.lastUpdate < endTime then
        failwith("Can't close until lastUpdate reached measureStartTime + measurePeriod")
    else skip;

    const lastAllowedTime : timestamp = endTime + int(event.maxAllowedMeasureLag);
    if param.lastUpdate > lastAllowedTime
    then failwith("Close failed: oracle time exceed maxAllowedMeasureLag")
    else skip;

    case event.closedOracleTime of [
    | Some(_p) -> failwith("Event already closed. Can't close event twice")
    | None -> skip
    ];

    (* Closing event: *)
    event.closedOracleTime := Some(param.lastUpdate);
    event.closedRate := Some(param.rate);

    const closeDynamics : nat = case event.startRate of [
    | Some(startRate) -> param.rate * store.targetDynamicsPrecision / startRate
    (* should not be here: *)
    | None -> (failwith("event.startRate is empty") : nat)
    ];

    event.closedDynamics := Some(closeDynamics);

    event.isClosed := True;
    event.isBetsAboveEqWin := Some(closeDynamics >= event.targetDynamics);

    (* Paying expirationFee for this method initiator: *)
    const operations : list(operation) =
        makeOperationsIfNotZero(Tezos.get_source(), event.expirationFee);

    event.expirationFee := 0tez;
    store.events[eventId] := event;

    (* Cleaning up event ID: *)
    store.closeCallId := (None : eventIdType);

} with (operations, store)
