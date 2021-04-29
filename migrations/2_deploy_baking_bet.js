const BakingBet = artifacts.require("BakingBet");
const { MichelsonMap } = require("@taquito/taquito");

const initialStorage = {
  events: new MichelsonMap(),
  betsForWinningLedger: new MichelsonMap(),
  betsAgainstWinningLedger: new MichelsonMap(),
  providedLiquidityLedger: new MichelsonMap(),
  liquidityForBonusLedger: new MichelsonMap(),
  liquidityAgainstBonusLedger: new MichelsonMap(),
  lastEventId: 0,
  closeCallEventId: null,
  measurementStartCallEventId: null,
};

module.exports = deployer => {
  deployer.deploy(BakingBet, initialStorage);
};
