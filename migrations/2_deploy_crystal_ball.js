const CrystalBall = artifacts.require("CrystalBall");
const { MichelsonMap } = require("@taquito/taquito");
const { pkh } = require("../faucet.json");

const initialStorage = {
  currencyPair: "XTZ-USD",
  targetRate: 0,
  targetTime: "",
  betsForLedger: new MichelsonMap(),
  betsAgainstLedger: new MichelsonMap(),
  oracleAddress: "KT1RCNpUEDjZAYhabjzgz1ZfxQijCDVMEaTZ",
  adminAddress: pkh,
  debugTime: "",  // TODO: remove me!
  debugRate: 0,  // TODO: remove me!
};

module.exports = deployer => {
  deployer.deploy(CrystalBall, initialStorage);
};
