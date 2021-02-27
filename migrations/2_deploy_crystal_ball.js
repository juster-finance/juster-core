const CrystalBall = artifacts.require("CrystalBall");
const { MichelsonMap } = require("@taquito/taquito");
const { pkh } = require("../faucet.json");

const initialStorage = {
  currencyPair: "",
  targetRate: 0,
  targetTime: 0,
  betsForLedger: new MichelsonMap(),
  betsAgainstLedger: new MichelsonMap(),
  oracleAddress: "KT1VsWxgE683MiXoaevLbXtpJqpWrcaWaQV7",
  adminAddress: pkh,
};

module.exports = deployer => {
  deployer.deploy(CrystalBall, initialStorage);
};
