(* Sets all new event config parameters to default *)
#include "../../partial/juster/juster_types.ligo"

const oneHour : nat = 60n*60n;
const oneDay : nat = oneHour*24n;

function lambda (const _config : configType) : configType is
record[
    measureStartFee = 200_000mutez;
    expirationFee = 100_000mutez;
    rewardCallFee = 200_000mutez;
    oracleAddress = ("KT1MwuujtBodVQFm1Jk1KTGNc49wygqoLvpe" : address);
    minMeasurePeriod = 60n*5n;
    maxMeasurePeriod = 31n*oneDay;
    minPeriodToBetsClose = 60n*5n;
    maxPeriodToBetsClose = 31n*oneDay;
    minLiquidityPercent = 0n;
    maxLiquidityPercent = 300_000n;  // 30% for 1_000_000 liquidityPrecision
    maxAllowedMeasureLag = oneHour;
    rewardFeeSplitAfter = oneDay;
    providerProfitFee = 100_000n;  // 10%
    isEventCreationPaused = False;
]

