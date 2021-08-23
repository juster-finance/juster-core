const { mnemonic, secret, password, email } = require("./faucet.json");

module.exports = {
  contracts_directory: "./contracts/main",
  networks: {
    development: {
      host: "https://granadanet.smartpy.io/",
      port: 443,
      network_id: "*",
      secret,
      mnemonic,
      password,
      email,
      type: "tezos"
    }
  }
}
