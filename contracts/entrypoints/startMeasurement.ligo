function startMeasurement(
    var eventId : nat;
    var store : storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    case store.measurementStartCallId of
    | Some(measurementStartCallId) ->
        failwith("Another call to oracle in process (should not be here)")
    | None -> skip
    end;

    const operations = makeCallToOracle(
        eventId,
        store,
        (Tezos.self("%startMeasurementCallback") : callbackEntrypoint));
    store.measurementStartCallId := Some(eventId);

} with (operations, store)
