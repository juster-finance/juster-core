function startMeasurement(
    var eventId : nat;
    var s : storage) : (list(operation) * storage) is
block {
    case s.measurementStartCallId of
    | Some(measurementStartCallId) ->
        failwith("Another call to oracle in process (should not be here)")
    | None -> skip
    end;

    const operations = makeCallToOracle(
        eventId,
        s,
        (Tezos.self("%startMeasurementCallback") : callbackEntrypoint));
    s.measurementStartCallId := Some(eventId);

} with (operations, s)
