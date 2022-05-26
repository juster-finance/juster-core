module PoolErrors is {
    const notEntryOwner : string = "Not entry position owner";
    const entryNotFound : string = "Entry is not found";
    const positionNotFound : string = "Position is not found";
    const eventNotFound : string = "Event is not found";
    const earlyApprove : string = "Cannot approve liquidity before acceptAfter";
    const notPositionOwner : string = "Not position owner";
    const noLiquidity : string = "Not enough liquidity to run event";
    const noFreeEventSlots : string = "Max active events limit reached";
    const lineNotFound : string = "Line is not found";
    const lineIsPaused : string = "Line is paused";
    const emptyLine : string = "Line should have at least one event";
    const depositIsPaused : string = "Deposit is paused";
    const justerNewEventNotFound : string = "Juster.newEvent is not found";
    const justerGetNextEventIdNotFound : string = "Juster.getNextEventId view is not found";
    const justerProvideLiquidityNotFound : string = "Juster.provideLiquidity is not found";
    const justerGetConfigNotFound : string = "Juster.getConfig is not found";
    const activeNotFound : string = "Active event is not found";
    const notExpectedAddress : string = "Address is not expected";
    const eventIdTaken : string = "Event id is already taken";
    const eventNotReady : string = "Event cannot be created until previous event betsCloseTime";
    const exceedClaimShares : string = "Claim shares is exceed position shares";
    const zeroAmount : string = "Should provide tez";
    const eventNotFinished : string = "Event result is not received yet";
    const claimNotFound : string = "Claim is not found";
}

module PoolWrongState is {
    const negativeEvents : string = "Wrong state: negative events";
    const negativeTotalLiquidity : string = "Wrong state: negative total liquidity";
    const negativeEntryLiquidity : string = "Wrong state: negative entry liquidity";
    const negativePayout : string = "Wrong state: negative payout";
    const negativeTotalShares : string = "Wrong state: negative total shares";
    const negativeActiveLiquidity : string = "Wrong state: negative active liquidity";
    const negativeActiveLiquidity : string = "Wrong state: negative active liquidity";
    const negativeWithdrawableLiquidity : string = "Wrong state: negative withdrawable liquidity";
    const negativeDuration : string = "Wrong state: negative duration";
    const lockedExceedTotal : string = "Wrong state: locked exceed total";
}
