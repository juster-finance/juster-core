(* Sets all new event config parameters to default *)
#include "../partials/types.ligo"

const oneHour : nat = 60n*60n;
const oneDay : nat = oneHour*24n;

function lambda (var newEventConfig : newEventConfigType) : newEventConfigType is
record[
    measureStartFee = 200_000mutez;
    expirationFee = 100_000mutez;
    rewardCallFee = 200_000mutez;
    oracleAddress = ("KT1SUP27JhX24Kvr11oUdWswk7FnCW78ZyUn" : address);
    minMeasurePeriod = 60n*5n;
    maxMeasurePeriod = 31n*oneDay;
    minPeriodToBetsClose = 60n*5n;
    maxPeriodToBetsClose = 31n*oneDay;
    liquidityPercent = 0n;
    maxAllowedMeasureLag = oneHour*4n;
    defaultTime = ("2018-06-30T07:07:32Z" : timestamp);
]
