const BakingBet = artifacts.require("BakingBet");
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
  defaultTime: '2018-06-30T07:07:32Z',
};

const initialStorage = {  
  events: new MichelsonMap(),
  betsFor: new MichelsonMap(),
  betsAgainst: new MichelsonMap(),
  providedLiquidityFor: new MichelsonMap(),
  providedLiquidityAgainst: new MichelsonMap(),
  liquidityShares: new MichelsonMap(),
  depositedBets: new MichelsonMap(),
  lastEventId: 0,
  closeCallEventId: null,
  measurementStartCallEventId: null,
  newEventConfig: config,
  manager: pkh,

  targetDynamicsPrecision: 1000000,
  sharePrecision: 100000000,
  liquidityPrecision: 1000000,
  ratioPrecision: 100000000,
};

module.exports = deployer => {
  deployer.deploy(BakingBet, initialStorage);
};
