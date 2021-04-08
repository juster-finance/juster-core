const { mnemonic, secret, password, email } = require("./faucet.json");

module.exports = {
  networks: {
    development: {
      host: "https://florencenet.smartpy.io",
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
