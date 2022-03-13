(* TODO: move all errors here *)
module Errors is {
    const disallowAmount : string = "Including tez using this entrypoint call is not allowed";
    const notManager : string = "Not a contract manager";
    const wrongState : string = "Wrong state";
    const notPositionOwner : string = "Not entry position owner";
    const entryNotFound : string = "Entry position is not found";
    const positionNotFound : string = "Position is not found";
    const eventNotFound : string = "Event is not found";
    const earlyApprove : string = "Cannot approve liquidity before acceptAfter";
    const noActiveEvents : string = "Need to have at least one line";
}
