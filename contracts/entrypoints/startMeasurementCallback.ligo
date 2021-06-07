function startMeasurementCallback(
    const params : callbackReturnedValueMichelson;
    var store : storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    const param : callbackReturnedValue = Layout.convert_from_right_comb(params);

    const eventId : nat = case store.measurementStartCallId of
    | Some(measurementStartCallId) -> measurementStartCallId
    | None -> (failwith("measurementStartCallId is empty") : nat)
    end;

    const event : eventType = getEvent(store, eventId);

    (* Check that callback runs from right address and with right
        currency pair: *)
    if Tezos.sender =/= event.oracleAddress
    then failwith("Unknown sender") else skip;
    if param.currencyPair =/= event.currencyPair
    then failwith("Unexpected currency pair") else skip;

    case event.measureOracleStartTime of
    | Some(time) -> failwith("Measurement period already started")
    | None -> skip
    end;

    if event.betsCloseTime > param.lastUpdate
    then failwith("Can't start measurement untill oracle time > betsCloseTime")
    else skip;

    const lastAllowedTime : timestamp =
        event.betsCloseTime + int(event.maxAllowedMeasureLag);
    if param.lastUpdate > lastAllowedTime
    then failwith("Measurement failed: oracle time exceed maxAllowedMeasureLag")
    else skip;

    (* Starting measurement: *)
    event.measureOracleStartTime := Some(param.lastUpdate);
    event.startRate := param.rate;

    (* Paying measureStartFee for this method initiator: *)
    const operations : list(operation) =
        makeOperationsIfNotZero(Tezos.source, event.measureStartFee);

    event.measureStartFee := 0tez;
    store.events[eventId] := event;

    (* Cleaning up event ID: *)
    store.measurementStartCallId := (None : eventIdType);

} with (operations, store)
