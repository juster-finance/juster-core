#include "types.ligo"
#include "tools.ligo"
#include "entrypoints/newEvent.ligo"
#include "entrypoints/bet.ligo"
#include "entrypoints/provideLiquidity.ligo"
#include "entrypoints/close.ligo"
#include "entrypoints/closeCallback.ligo"
#include "entrypoints/startMeasurement.ligo"
#include "entrypoints/startMeasurementCallback.ligo"
#include "entrypoints/withdraw.ligo"


function main (var params : action; var s : storage) : (list(operation) * storage) is
case params of
| NewEvent(p) -> ((nil: list(operation)), newEvent(p, s))
| Bet(p) -> ((nil: list(operation)), bet(p, s))
| ProvideLiquidity(p) -> ((nil: list(operation)), provideLiquidity(p, s))
| StartMeasurement(p) -> (startMeasurement(p, s))
| StartMeasurementCallback(p) -> (startMeasurementCallback(p, s))
| Close(p) -> (close(p, s))
| CloseCallback(p) -> (closeCallback(p, s))
| Withdraw(p) -> withdraw(p, s)
end
