function isStartFailed(const event : eventType) : bool is
block {
    const startTimeLag : int = Tezos.now - event.betsCloseTime;
    const isFailed : bool = (
        startTimeLag > 0
        and (abs(startTimeLag) > event.maxAllowedMeasureLag));
} with isFailed


function isCloseFailed(const event : eventType) : bool is
block {
    const closeTimeLag : int =
        Tezos.now - event.betsCloseTime - event.measurePeriod;
    const isFailed : bool = (
        (closeTimeLag > 0)
        and (abs(closeTimeLag) > event.maxAllowedMeasureLag));
} with isFailed


function triggerForceMajeure(
    const eventId : nat;
    var store: storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    const event : eventType = getEvent(store, eventId);
    (* fees agregates all unpaid fees for oracle calls: *)
    var operations : list(operation) := nil;

    (* Force Majeure case 1: start measurement lag is too long: *)
    const isStartMeasurementFailed : bool = case event.measureOracleStartTime of
    | Some(time) -> False
    | None -> isStartFailed(event)
    end;

    (* Force Majeure case 2: close lag is too long: *)
    const isCloseFailed : bool = case event.closedOracleTime of
    | Some(time) -> False
    | None -> isCloseFailed(event)
    end;

    (* Triggering Force Majeure: *)
    if isStartMeasurementFailed or isCloseFailed then
    block {
        const receiver : contract(unit) = getReceiver(Tezos.sender);
        const fees : tez = event.measureStartFee + event.expirationFee;
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
