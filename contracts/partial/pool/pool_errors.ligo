(* TODO: move all errors here *)
(* TODO: rename to AggregatorErrors *)
module PoolErrors is {
    const wrongState : string = "Wrong state";
    const notEntryOwner : string = "Not entry position owner";
    const entryNotFound : string = "Entry is not found";
    const positionNotFound : string = "Position is not found";
    const eventNotFound : string = "Event is not found";
    const earlyApprove : string = "Cannot approve liquidity before acceptAfter";
    const noActiveEvents : string = "Need to have at least one line";
    const notPositionOwner : string = "Not position owner";
    const noLiquidity : string = "Not enough liquidity to run event";
    const noFreeEventSlots : string = "Max active events limit reached";
    const lineNotFound : string = "Line is not found";
    const lineIsPaused : string = "Line is paused";
    const emptyLine : string = "Line should have at least one event";
    const depositIsPaused : string = "Deposit is paused"
}
