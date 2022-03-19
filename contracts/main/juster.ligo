#include "../partial/common_errors.ligo"
#include "../partial/common_helpers.ligo"
#include "../partial/juster/juster_types.ligo"
#include "../partial/juster/juster_errors.ligo"
#include "../partial/juster/juster_helpers.ligo"
#include "../partial/juster/entrypoints/new_event.ligo"
#include "../partial/juster/entrypoints/bet.ligo"
#include "../partial/juster/entrypoints/provide_liquidity.ligo"
#include "../partial/juster/entrypoints/close.ligo"
#include "../partial/juster/entrypoints/close_callback.ligo"
#include "../partial/juster/entrypoints/start_measurement.ligo"
#include "../partial/juster/entrypoints/start_measurement_callback.ligo"
#include "../partial/juster/entrypoints/withdraw.ligo"
#include "../partial/juster/entrypoints/update_config.ligo"
#include "../partial/juster/entrypoints/trigger_force_majeure.ligo"
#include "../partial/juster/entrypoints/set_delegate.ligo"
#include "../partial/juster/entrypoints/default.ligo"
#include "../partial/juster/entrypoints/claim_baking_rewards.ligo"
#include "../partial/juster/entrypoints/claim_retained_profits.ligo"
#include "../partial/juster/entrypoints/change_manager.ligo"
#include "../partial/juster/entrypoints/accept_ownership.ligo"


type action is
| NewEvent of newEventParams
| ProvideLiquidity of provideLiquidityParams
| Bet of betParams
| StartMeasurement of nat
| StartMeasurementCallback of callbackReturnedValue
| Close of nat
| CloseCallback of callbackReturnedValue
| Withdraw of withdrawParams
| UpdateConfig of updateConfigParam
| TriggerForceMajeure of nat
| SetDelegate of option (key_hash)
| Default of unit
| ClaimBakingRewards of unit
| ClaimRetainedProfits of unit
| ChangeManager of address
| AcceptOwnership of unit


function main (const params : action; var s : storage) : (list(operation) * storage) is
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
| ClaimRetainedProfits(p)     -> claimRetainedProfits(p, s)
| ChangeManager(p)            -> changeManager(p, s)
| AcceptOwnership(p)          -> acceptOwnership(p, s)
end

#include "../partial/juster/entrypoints/views.ligo"

