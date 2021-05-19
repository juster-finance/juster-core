function triggerForceMajeure(
    var eventId : nat;
    var store: storage) : (list(operation) * storage) is
block {

    const event : eventType = getEvent(store, eventId);

    (* Force Majeure case 1: start measurement lag is too long: *)
    const startTimeLag : int = Tezos.now - event.betsCloseTime;
    const isStartMeasurementFailed : bool = (
        (startTimeLag > 0)
        and (abs(startTimeLag) > event.maxAllowedMeasureLag)
        and (not event.isMeasurementStarted));

    (* Force Majeure case 2: close lag is too long: *)
    const closeTimeLag : int =
        Tezos.now - event.betsCloseTime - event.measurePeriod;
    const isCloseFailed : bool = (
        (closeTimeLag > 0)
        and (abs(closeTimeLag) > event.maxAllowedMeasureLag)
        and (not event.isClosed));

    var operations : list(operation) := nil;
    var fees : tez := 0tez;

    (* Triggering Force Majeure: *)
    if isStartMeasurementFailed or isCloseFailed then
    block {
        (* startMeasurement fee and expiration fee goes to sender: *)
        if not event.isMeasurementStarted then
            fees := fees + event.measureStartFee
        else skip;

        if not event.isClosed then
            fees := fees + event.expirationFee
        else skip;

        const receiver : contract(unit) = getReceiver(Tezos.sender);
        const operation : operation = Tezos.transaction(unit, fees, receiver);
        if fees > 0tez then
            operations := operation # operations
        else skip;

        (* Closing event with ForceMajeure flag setted True: *)
        event.isForceMajeure := True;
        event.isClosed := True;
        store.events[eventId] := event;
    }
    else failwith("None of the Force Majeure scenarios are occurred");

} with (operations, store)
