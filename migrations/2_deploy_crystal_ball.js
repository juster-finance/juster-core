const CrystalBall = artifacts.require("CrystalBall");
const { MichelsonMap } = require("@taquito/taquito");
const { pkh } = require("../faucet.json");

const initialStorage = {
  currencyPair: "XTZ-USD",
  targetRate: 0,
  targetTime: "",
  betsForLedger: new MichelsonMap(),
  betsAgainstLedger: new MichelsonMap(),
  oracleAddress: "KT1Age13nBE2VXxTPjwVJiE8Jbt73kumwxYx",
  isClosed: false,
  closedTime: "",
  closedRate: 0,
  betsForSum: 0,
  betsAgainstSum: 0,
  isBetsForWin: false,
};

module.exports = deployer => {
  deployer.deploy(CrystalBall, initialStorage);
};
