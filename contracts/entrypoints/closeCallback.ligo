function closeCallback(
    var params : callbackReturnedValueMichelson;
    var store : storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    const eventId : nat = case store.closeCallId of
    | Some(closeCallId) -> closeCallId
    | None -> (failwith("closeCallId is empty") : nat)
    end;

    (* TODO: Check that current time is not far away from measurementStartTime
        + timedelta, if it is, run Force Majeure. Give Manager ability to
        control this timedelta *)

    const param : callbackReturnedValue = Layout.convert_from_right_comb(params);

    const event : eventType = getEvent(store, eventId);

    (* Check that callback runs from right address
        and with right currency pair: *)
    if Tezos.sender =/= event.oracleAddress
    then failwith("Unknown sender") else skip;
    if param.currencyPair =/= event.currencyPair
    then failwith("Unexpected currency pair") else skip;

    if not event.isMeasurementStarted then
        failwith("Can't close contract before measurement period started")
    else skip;

    const endTime : timestamp =
        event.measureOracleStartTime + int(event.measurePeriod);
    if param.lastUpdate < endTime then
        failwith("Can't close until lastUpdate reached measureStartTime + measurePeriod")
    else skip;

    const lastAllowedTime : timestamp = endTime + int(event.maxAllowedMeasureLag);
    if param.lastUpdate > lastAllowedTime
    then failwith("Close failed: oracle time exceed maxAllowedMeasureLag")
    else skip;

    if event.isClosed then failwith("Contract already closed. Can't close contract twice")
    else skip;

    (* Closing contract: *)
    event.closedOracleTime := param.lastUpdate;
    event.closedRate := param.rate;
    event.closedDynamics :=
        param.rate * store.targetDynamicsPrecision / event.startRate;
    event.isClosed := True;
    event.isBetsAboveEqWin := event.closedDynamics >= event.targetDynamics;

    (* Paying expirationFee for this method initiator: *)
    const operations : list(operation) =
        makeOperationsIfNotZero(Tezos.source, event.expirationFee);

    store.events[eventId] := event;

    (* Cleaning up event ID: *)
    store.closeCallId := (None : eventIdType);

    (* TODO: this close/measurement callbacks have a lot similarities, maybe
        there are some code that can be moved in separate function
        (for example check for the oracle, but maybe it is okay to have copycode here) *)

} with (operations, store)
