#include "../partials/types.ligo"
#include "../partials/tools.ligo"
#include "../entrypoints/newEvent.ligo"
#include "../entrypoints/bet.ligo"
#include "../entrypoints/provideLiquidity.ligo"
#include "../entrypoints/close.ligo"
#include "../entrypoints/closeCallback.ligo"
#include "../entrypoints/startMeasurement.ligo"
#include "../entrypoints/startMeasurementCallback.ligo"
#include "../entrypoints/withdraw.ligo"
#include "../entrypoints/updateConfig.ligo"
#include "../entrypoints/triggerForceMajeure.ligo"
#include "../entrypoints/setDelegate.ligo"
#include "../entrypoints/default.ligo"
#include "../entrypoints/claimBakingRewards.ligo"


function main (var params : action; var s : storage) : (list(operation) * storage) is
case params of
| NewEvent(p)                 -> newEvent(p, s)
| Bet(p)                      -> bet(p, s)
| ProvideLiquidity(p)         -> provideLiquidity(p, s)
| StartMeasurement(p)         -> startMeasurement(p, s)
| StartMeasurementCallback(p) -> startMeasurementCallback(p, s)
| Close(p)                    -> close(p, s)
| CloseCallback(p)            -> closeCallback(p, s)
| Withdraw(p)                 -> withdraw(p, s)
| UpdateConfig(p)             -> updateConfig(p, s)
| TriggerForceMajeure(p)      -> triggerForceMajeure(p, s)
| SetDelegate(p)              -> setDelegate(p, s)
| Default(p)                  -> default(p, s)
| ClaimBakingRewards(p)       -> claimBakingRewards(p, s)
end
