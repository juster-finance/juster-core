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
