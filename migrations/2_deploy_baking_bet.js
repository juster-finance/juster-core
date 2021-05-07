const BakingBet = artifacts.require("BakingBet");
const { MichelsonMap } = require("@taquito/taquito");

const initialStorage = {
  events: new MichelsonMap(),
  betsFor: new MichelsonMap(),
  betsAgainst: new MichelsonMap(),
  providedLiquidity: new MichelsonMap(),
  liquidityForShares: new MichelsonMap(),
  liquidityAgainstShares: new MichelsonMap(),
  forProfitDiff: new MichelsonMap(),
  againstProfitDiff: new MichelsonMap(),
  depositedBets: new MichelsonMap(),
  lastEventId: 0,
  closeCallEventId: null,
  measurementStartCallEventId: null,
};

module.exports = deployer => {
  deployer.deploy(BakingBet, initialStorage);
};
