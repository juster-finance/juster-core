function close(
    const eventId : nat;
    var store : storage) : (list(operation) * storage) is
block {

    checkNoAmountIncluded(unit);

    (* When calling close event, s.closeCallId should be equal to None,
        otherwise it looks like another callback is runned but no answer
        is received yet (is it even possible, btw?) *)
    case store.closeCallId of
    | Some(closeCallId) ->
        failwith("Another call to oracle in process (should not be here)")
    | None -> skip
    end;

    const operations = makeCallToOracle(
        eventId, store, (Tezos.self("%closeCallback") : callbackEntrypoint));
    store.closeCallId := Some(eventId);

} with (operations, store)
