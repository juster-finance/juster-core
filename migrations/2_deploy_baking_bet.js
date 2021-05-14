const BakingBet = artifacts.require("BakingBet");
const { MichelsonMap } = require("@taquito/taquito");

const config = {
  measureStartFee: 100000,
  expirationFee: 100000,
  rewardCallFee: 100000,
  oracleAddress: 'KT1RCNpUEDjZAYhabjzgz1ZfxQijCDVMEaTZ',
  targetDynamicsPrecision: 1000000,
  sharePrecision: 100000000,
  liquidityPrecision: 1000000,
  ratioPrecision: 100000000,
  minMeasurePeriod: 60*5,  // 5 mins
  maxMeasurePeriod: 60*60*24*31,  // 31 days
  minPeriodToBetsClose: 60*5,
  maxPeriodToBetsClose: 60*60*24*31,
  liquidityPercent: 0,
  minPoolSize: 0,
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
  oracleAddress: 'KT1RCNpUEDjZAYhabjzgz1ZfxQijCDVMEaTZ',
  newEventConfig: config,
};

module.exports = deployer => {
  deployer.deploy(BakingBet, initialStorage);
};
