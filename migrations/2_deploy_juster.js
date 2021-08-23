const Juster = artifacts.require("Juster");
const { MichelsonMap } = require("@taquito/taquito");
const { pkh } = require("../faucet.json");

const config = {
  measureStartFee: 100000,
  expirationFee: 100000,
  rewardCallFee: 100000,
  oracleAddress: 'KT1SUP27JhX24Kvr11oUdWswk7FnCW78ZyUn',
  minMeasurePeriod: 60*5,  // 5 mins
  maxMeasurePeriod: 60*60*24*31,  // 31 days
  minPeriodToBetsClose: 60*5,
  maxPeriodToBetsClose: 60*60*24*31,
  minLiquidityPercent: 0,
  maxLiquidityPercent: 300000,
  maxAllowedMeasureLag: 60*60*4,
  rewardFeeSplitAfter: 60*60*24,  // one day
  providerProfitFee: 100000,  // 10%
  isEventCreationPaused: false,
};

const initialStorage = {
  events: new MichelsonMap(),
  betsAboveEq: new MichelsonMap(),
  betsBelow: new MichelsonMap(),
  providedLiquidityAboveEq: new MichelsonMap(),
  providedLiquidityBelow: new MichelsonMap(),
  liquidityShares: new MichelsonMap(),
  depositedBets: new MichelsonMap(),
  nextEventId: 0,
  closeCallEventId: null,
  measurementStartCallEventId: null,
  config: config,
  manager: pkh,

  targetDynamicsPrecision: 1000000,
  sharePrecision: 100000000,
  liquidityPrecision: 1000000,
  ratioPrecision: 100000000,
  providerProfitFeePrecision: 1000000,
  bakingRewards: 0,
  retainedProfits: 0,
  proposedManager: null
};

module.exports = deployer => {
  deployer.deploy(Juster, initialStorage);
};
