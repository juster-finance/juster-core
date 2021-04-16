const CrystalBall = artifacts.require("CrystalBall");
const { MichelsonMap } = require("@taquito/taquito");
const { pkh } = require("../faucet.json");

const initialStorage = {
  events: new MichelsonMap(),
  betsForLedger: new MichelsonMap(),
  betsAgainstLedger: new MichelsonMap(),
  liquidityLedger: new MichelsonMap(),
  lastEventId: 0,
  closeCallEventId: null,
  measurementStartCallEventId: null,
};

module.exports = deployer => {
  deployer.deploy(CrystalBall, initialStorage);
};
