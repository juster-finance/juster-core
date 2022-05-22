# Juster core:
## Entrypoints:
### newEvent
- Expects `newEventParams` as parameter
- Anyone can call this entrypoint
- Creates new event with given params if they are valid
- TODO: describe all validations

### provideLiquidity
- Expects `provideLiquidityParams` as parameter
- Anyone can call this entrypoint
- TODO: add provide liquidity shares calculation formula

### bet
- Expects `betParams` as parameter
- Anyone can call this entrypoint
- TODO: add bet reward calculation formula
- TODO: describe fee

### startMeasurement
- Expects `nat` as parameter
- Anyone can call this entrypoint

### startMeasurementCallback
- Expects `callbackReturnedValue` as parameter
- Only oracle that set in `storage` can call this entrypoint

### close
- Expects `nat` as parameter
- Anyone can call this entrypoint

### closeCallback
- Expects `callbackReturnedValue` as parameter
- Only oracle that set in `storage` can call this entrypoint

### withdraw
- Expects `withdrawParams` as parameter
- Anyone can call this entrypoint

### updateConfig
- Expects `updateConfigParam` as parameter

### triggerForceMajeure
- Expects `nat` as parameter

### setDelegate
- Expects `option (key_hash)` as parameter where `key_hash` is public key hash of new delegate
- Sets contract delegate to provided `key_hash`

### default
- Expects `unit` as parameter

### claimBakingRewards
- Expects `unit` as parameter

### claimRetainedProfits
- Expects `unit` as parameter

### changeManager
- Expects `address` as parameter

### acceptOwnership
- Expects `unit` as parameter


## default
- Expects `unit` as parameter
- Expects some xtz amount attached to the transaction
- Returns operations with distributed splits to participants
- Changes storage `undistributed` ledger
- Changes storage `residuals` sum
- Anyone can call this entrypoint
- Behaviour depends on `threshold` settings
- Some xtz amount might be locked in `residuals`

This entrypoint allows HicProxy contract to receive xtz and split it among participants. When this contract used as a recepient of xtz (as a seller in the marketplace or as a royalty receiver) it runs logic that redistribute incoming value using participant shares. By default all incoming values automaticly sent to participants, but admin can set threshold that determines the minimal value that will trigger automatic payout to participant. If value is less than threshold it will be kept in contract until it reaches it. If incoming amount can't be split equally between all participants, the residuals left on the contract and will be reused next time contract recieves some payment (during next `default` call).

