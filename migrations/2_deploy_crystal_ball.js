const CrystalBall = artifacts.require("CrystalBall");
const { MichelsonMap } = require("@taquito/taquito");
const { pkh } = require("../faucet.json");

const initialStorage = {
  currencyPair: "XTZ-USD",
  createdTime: "1617976565",
  targetDynamics: 1000000,
  betsCloseTime: "1618062965", // TODO: get current time here and add 24h
  measureStartTime: "",
  measureOracleStartTime: "",
  isMeasurementStarted: false,
  startRate: 0,
  measurePeriod: 12*60*60,
  isClosed: false,
  closedTime: "",
  closedOracleTime: "",
  closedRate: 0,
  closedDynamics: 0,
  isBetsForWin: false,

  betsForLedger: new MichelsonMap(),
  betsAgainstLedger: new MichelsonMap(),
  liquidityLedger: new MichelsonMap(),

  oracleAddress: "KT1SUP27JhX24Kvr11oUdWswk7FnCW78ZyUn",

  betsForSum: 0,
  betsAgainstSum: 0,
  liquiditySum: 0,

  liquidityPercent: 0,
  measureStartFee: 0,
  expirationFee: 0,
};

module.exports = deployer => {
  deployer.deploy(CrystalBall, initialStorage);
};
