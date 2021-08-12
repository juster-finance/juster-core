# Juster Maker
This is pytezos asyncio tool used to run Juster event lines.

### Run Juster Maker:
1. Install pytezos: https://pytezos.org/quick_start.html#installation
2. Install other dependencies (pytest, sgqlc):
```
pip install -r requirements.txt
```
3. Add your key to config.py (you can use faucet to get testnet tokens:
https://faucet.tzalpha.net/)
4. Run tests:
```
pytest -v
```
5. Run maker:
```
python run_maker.py
```

### Description:
- **JusterMaker**: tool that allow to run multiple Executors in parallel
- executors/ directory with different objects each of them represent one task
    * **Executor**: basic executor class that used in each executor
    * **EventExecutor**: basic executor used for different Juster Maker event tasks
    * **NewEventCaller**: executor that creates new event for one **EventLine**
    * **ProvideLiquidityCaller**: executor that provides liquidity for one **EventLine**
    * **WithdrawFinishedCaller**: executor that calls withdraw for transactions that was
not withdrawn by users (and getting reward for doing this)
    * **WithdrawCanceledCaller**: executor that calls withdraw for canceled events
(events that was finished by ForceMajeure call)
    * **ForceMajeureCaller**: executor that checks if there are any events that have
missing startMeasurement/close calls and runs TriggerForceMajeure
    * **BulkSender**: executor that monitors operations queue and makes bulk
transactions for required operations
    * TODO: **StartMeasurementCaller**
    * TODO: **CloseCaller**
    * TODO: **HarbingerPusher**
- **JusterDipDupClient**: tool used to make queries to juster dipdup GraphQL endpoint
- **EventLines**: tool to create list of **EventLine** and save them into **event_lines.json**
- **EventLine** represents one repeated event with given currency pair, measure period
and target ratio
- run_maker.py: CLI tool to run JusterMaker
- config.py: separate file with all settings used across maker

### TODO:
- make tests for each Executor
- dipdup subscription instead of asyncio.sleep in executors
- integrate with Harbinger pusher, startMeasurement, close calls
- improved liquidity provider with different ratio for events based on coinbase data

