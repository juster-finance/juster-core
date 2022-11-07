import math
import time
from decimal import Decimal
from os.path import dirname
from os.path import join
from unittest import TestCase

from pytezos import ContractInterface
from pytezos import MichelsonRuntimeError
from pytezos import pytezos

from models.pool import ClaimKey
from models.pool import PoolModel
from tests.test_data import ONE_DAY
from tests.test_data import ONE_HOUR
from tests.test_data import generate_juster_config
from tests.test_data import generate_line_params
from tests.test_data import generate_pool_storage

POOL_FN = '../../../build/contracts/pool.tz'
RUN_TIME = int(time.time())


class PoolBaseTestCase(TestCase):
    """Methods used to check different state transformations for Pool
    Each check method runs one transaction and then compare storage
    before and after transaction execution. At the end each check
    method returns new storage
    """

    def setUp(self):
        self.pool = ContractInterface.from_file(
            join(dirname(__file__), POOL_FN)
        )

        # four participants and their pk hashes:
        self.a = 'tz1iQE8ijR5xVPffBUPFubwB9XQJuyD9qsoJ'
        self.b = 'tz1MdaJfWzP5pPx3gwPxfdLZTHW6js9havos'
        self.c = 'tz1RS9GoEXakf9iyBmSaheLMcakFRtzBXpWE'
        self.d = 'tz1TdKuFwYgbPHHb7y1VvLH4xiwtAzcjwDjM'

        self.manager = self.a
        self.address = 'contract'

        self.juster_address = 'KT1SUP27JhX24Kvr11oUdWswk7FnCW78ZyUn'
        self.current_time = RUN_TIME
        self.level = 1

        self.init_storage = generate_pool_storage(manager=self.manager)

        self.drop_changes()

    def to_model(self, storage=None, balance=None):
        storage = self.storage if storage is None else storage
        balance = (
            Decimal(self.balances['contract']) if balance is None else balance
        )
        return PoolModel.from_storage(
            storage=storage,
            balance=balance,
            now=self.current_time,
            level=self.level,
        )

    def get_balance(self, address=None):
        address = self.address if address is None else address
        return int(self.balances[address])

    def drop_changes(self):
        self.storage = self.init_storage.copy()
        self.balances = {self.address: Decimal(0)}
        self.next_event_id = 0

    def update_balance(self, address, amount):
        """Used to track balances of different users"""
        self.balances[address] = (
            self.balances.get(address, Decimal(0)) + amount
        )
        self.assertTrue(self.balances['contract'] >= Decimal(0))

    def get_next_liquidity(self):
        """Returns next event liquidity value in int"""
        return int(self.to_model().calc_next_event_liquidity())

    def check_operation_is(self, operation, amount=None, destination=None):
        """Asserts that amount & destination of given operation is expected"""
        if amount is not None:
            self.assertEqual(amount, int(operation['amount']))
        if destination is not None:
            self.assertEqual(destination, operation['destination'])

    def add_line(
        self,
        sender=None,
        currency_pair='XTZ-USD',
        max_events=2,
        bets_period=3600,
        last_bets_close_time=0,
        amount=0,
        juster_address=None,
        min_betting_period=0,
        advance_time=0,
        measure_period=3600,
        is_paused=False,
    ):

        sender = sender or self.manager
        juster_address = juster_address or self.juster_address

        line_params = generate_line_params(
            currency_pair=currency_pair,
            max_events=max_events,
            bets_period=bets_period,
            last_bets_close_time=last_bets_close_time,
            juster_address=juster_address,
            min_betting_period=min_betting_period,
            advance_time=advance_time,
            measure_period=measure_period,
            is_paused=is_paused,
        )

        call = self.pool.addLine(line_params)
        result = call.with_amount(amount).interpret(
            storage=self.storage, now=self.current_time, sender=sender
        )

        init_model = self.to_model()
        line_id = init_model.add_line(
            measure_period=measure_period,
            bets_period=bets_period,
            last_bets_close_time=last_bets_close_time,
            max_events=max_events,
            is_paused=is_paused,
            min_betting_period=min_betting_period,
        )

        result_model = self.to_model(storage=result.storage)
        self.assertEqual(init_model, result_model)

        added_line = result.storage['lines'][line_id]
        self.assertEqual(added_line['currencyPair'], currency_pair)
        self.assertEqual(added_line['juster'], juster_address)
        self.assertEqual(added_line['advanceTime'], advance_time)

        self.storage = result.storage
        return line_id

    def deposit_liquidity(self, sender=None, amount=1_000_000):
        sender = sender or self.manager
        new_balance = self.get_balance(self.address) + amount

        call = self.pool.depositLiquidity()
        result = call.with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            balance=new_balance,
        )

        init_model = self.to_model()
        entry_id = init_model.deposit_liquidity(
            user=sender, amount=Decimal(amount)
        )

        result_model = self.to_model(
            storage=result.storage, balance=new_balance
        )

        self.assertEqual(init_model, result_model)

        self.assertEqual(
            result.storage['entryLiquidityF'],
            result_model.calc_entry_liquidity_f(),
        )

        self.storage = result.storage
        self.update_balance(self.address, amount)
        self.update_balance(sender, -amount)

        return entry_id

    def approve_entry(self, sender=None, entry_id=0, amount=0):
        sender = sender or self.manager
        call = self.pool.approveEntry(entry_id)
        result = call.with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            balance=self.get_balance(self.address),
        )

        self.assertTrue(result.storage['entries'][entry_id] is None)
        result.storage['entries'].pop(entry_id)

        init_model = self.to_model()
        provider = init_model.approve_entry(entry_id)
        result_model = self.to_model(storage=result.storage)
        self.assertEqual(init_model, result_model)

        self.storage = result.storage
        return provider

    def cancel_entry(self, sender=None, entry_id=0, amount=0):
        sender = sender or self.manager
        call = self.pool.cancelEntry(entry_id)
        init_balance = self.get_balance(self.address)
        result = call.with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            balance=init_balance,
        )

        self.assertTrue(result.storage['entries'][entry_id] is None)
        result.storage['entries'].pop(entry_id)

        init_model = self.to_model()
        init_model.cancel_entry(entry_id)

        entry = self.storage['entries'][entry_id]
        result_model = self.to_model(
            storage=result.storage,
            balance=init_balance - entry['amount']
        )
        self.assertEqual(init_model, result_model)

        self.assertEqual(len(result.operations), 1)
        self.check_operation_is(
            operation=result.operations[0],
            amount=entry['amount'],
            destination=entry['provider'],
        )

        self.storage = result.storage

        self.assertEqual(
            result.storage['entryLiquidityF'],
            result_model.calc_entry_liquidity_f(),
        )
        self.update_balance(entry['provider'], entry['amount'])

    def claim_liquidity(
        self, sender=None, provider=None, shares=1_000_000, amount=0
    ):
        sender = sender or self.manager
        provider = provider or self.manager
        params = {'provider': provider, 'shares': shares}

        call = self.pool.claimLiquidity(params)
        result = call.with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            balance=self.get_balance(self.address),
        )

        init_model = self.to_model()
        payout = init_model.claim_liquidity(provider, Decimal(shares))
        new_balance = self.get_balance(self.address) - payout
        result_model = self.to_model(
            storage=result.storage, balance=new_balance
        )
        self.assertEqual(init_model, result_model)

        if payout > Decimal(0):
            self.assertEqual(len(result.operations), 1)
            self.check_operation_is(
                result.operations[0],
                amount=payout,
                destination=provider,
            )
        else:
            self.assertEqual(len(result.operations), 0)

        self.storage = result.storage

        self.update_balance(self.address, -payout)
        self.update_balance(provider, payout)
        return payout

    def withdraw_claims(self, sender=None, claims=None, amount=0):
        sender = sender or self.manager
        default_claims = [dict(provider=self.manager, eventId=0)]
        claims = default_claims if claims is None else claims

        call = self.pool.withdrawClaims(claims)
        result = call.with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            balance=self.get_balance(self.address),
        )

        claim_keys = [ClaimKey.from_dict(claim) for claim in claims]
        init_model = self.to_model()
        payouts = init_model.withdraw_claims(claim_keys)
        new_balance = self.get_balance(self.address) - sum(payouts.values())

        for claim in claims:
            key = (claim['eventId'], claim['provider'])
            self.assertTrue(result.storage['claims'][key] is None)
            result.storage['claims'].pop(key)

        result_model = self.to_model(
            storage=result.storage, balance=new_balance
        )
        self.assertEqual(init_model, result_model)

        self.assertEqual(len(payouts), len(result.operations))

        if len(payouts):
            for operation in result.operations:
                participant = operation['destination']
                amount = payouts[participant]
                self.check_operation_is(
                    operation=operation, amount=amount, destination=participant
                )
                self.update_balance(self.address, -amount)
                self.update_balance(participant, amount)

        self.storage = result.storage
        return payouts

    def pay_reward(self, sender=None, event_id=0, amount=1_000_000):
        sender = sender or self.juster_address

        call = self.pool.payReward(event_id)
        result = call.with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            balance=self.get_balance(self.address),
        )

        init_model = self.to_model()
        init_model.pay_reward(event_id, Decimal(amount))
        new_balance = self.get_balance(self.address) + amount
        result_model = self.to_model(
            storage=result.storage, balance=Decimal(new_balance)
        )
        self.assertEqual(init_model, result_model)

        self.storage = result.storage
        self.update_balance(sender, -amount)
        self.update_balance(self.address, amount)

    def create_event(
        self, sender=None, line_id=0, next_event_id=None, amount=0, config=None
    ):

        sender = sender or self.manager
        next_event_id = next_event_id or self.next_event_id
        config = config or generate_juster_config(
            expiration_fee=0, measure_start_fee=0
        )

        contract_call = self.pool.createEvent(line_id)
        juster_address = self.storage['lines'][line_id]['juster']
        result = contract_call.with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            view_results={
                f'{juster_address}%getNextEventId': next_event_id,
                f'{juster_address}%getConfig': config,
            },
            balance=self.get_balance(self.address),
        )

        init_model = self.to_model()
        init_model.create_event(line_id, next_event_id)
        next_event_liquidity = self.to_model().calc_next_event_liquidity()
        new_balance = self.get_balance(self.address) - next_event_liquidity
        result_model = self.to_model(
            storage=result.storage, balance=Decimal(new_balance)
        )
        self.assertEqual(init_model, result_model)

        self.assertEqual(len(result.operations), 2)
        event_fee = config['expirationFee'] + config['measureStartFee']

        self.check_operation_is(
            operation=result.operations[0],
            amount=event_fee,
            destination=juster_address,
        )

        self.check_operation_is(
            operation=result.operations[1],
            amount=next_event_liquidity - event_fee,
            destination=juster_address,
        )

        self.storage = result.storage
        self.update_balance(self.address, -next_event_liquidity)
        self.update_balance(juster_address, next_event_liquidity)
        self.next_event_id += 1
        return next_event_id

    def trigger_pause_line(self, sender=None, line_id=0, amount=0):
        sender = sender or self.manager

        contract_call = self.pool.triggerPauseLine(line_id)
        result = contract_call.with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            balance=self.get_balance(self.address),
        )

        init_model = self.to_model()
        init_model.trigger_pause_line(line_id)
        result_model = self.to_model(storage=result.storage)
        self.assertEqual(init_model, result_model)

        self.storage = result.storage
        return result.storage['lines'][line_id]['isPaused']

    def trigger_pause_deposit(self, sender=None, amount=0):
        sender = sender or self.manager

        contract_call = self.pool.triggerPauseDeposit()
        result = contract_call.with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            balance=self.get_balance(self.address),
        )

        init_state = self.storage['isDepositPaused']
        result_state = result.storage['isDepositPaused']
        self.assertEqual(init_state, not result_state)

        self.storage = result.storage

        return result_state

    def set_entry_lock_period(self, sender=None, amount=0, new_period=0):
        sender = sender or self.manager

        contract_call = self.pool.setEntryLockPeriod(new_period)
        result = contract_call.with_amount(amount).interpret(
            storage=self.storage,
            now=self.current_time,
            sender=sender,
            balance=self.get_balance(self.address),
        )

        self.assertEqual(result.storage['entryLockPeriod'], new_period)

        self.storage = result.storage

    def propose_manager(self, sender=None, proposed_manager=None, amount=0):
        sender = sender or self.manager
        proposed_manager = proposed_manager or self.manager

        call = self.pool.proposeManager(proposed_manager).with_amount(amount)
        result = call.interpret(
            now=self.current_time, storage=self.storage, sender=sender
        )
        self.assertEqual(len(result.operations), 0)
        self.assertEqual(result.storage['proposedManager'], proposed_manager)

        self.storage = result.storage

    def accept_ownership(self, sender=None, amount=0):
        sender = sender or self.manager

        call = self.pool.acceptOwnership().with_amount(amount)
        result = call.interpret(
            now=self.current_time, storage=self.storage, sender=sender
        )
        self.assertEqual(len(result.operations), 0)
        self.assertEqual(result.storage['manager'], sender)

        self.storage = result.storage

    def set_delegate(self, sender=None, new_delegate=None, amount=0):
        sender = sender or self.manager
        new_delegate = new_delegate or self.c

        call = self.pool.setDelegate(new_delegate).with_amount(amount)
        result = call.interpret(
            now=self.current_time, storage=self.storage, sender=sender
        )
        self.assertEqual(len(result.operations), 1)
        op = result.operations[0]

        self.assertEqual(op['kind'], 'delegation')
        self.assertEqual(op['delegate'], new_delegate)

    def default(self, sender=None, amount=0):
        sender = sender or self.manager

        call = self.pool.default().with_amount(amount)
        result = call.interpret(
            now=self.current_time, storage=self.storage, sender=sender
        )
        self.assertEqual(len(result.operations), 0)
        self.storage = result.storage

        self.balances[sender] = self.balances.get(sender, 0) - amount
        self.balances['contract'] = self.balances.get('contract', 0) + amount

    def disband(self, sender=None, amount=0):
        sender = sender or self.manager

        call = self.pool.disband().with_amount(amount)
        result = call.interpret(
            now=self.current_time, storage=self.storage, sender=sender
        )
        self.assertEqual(len(result.operations), 0)
        assert result.storage['isDisbandAllow']
        self.storage = result.storage

    def get_line(self, line_id):
        return self.pool.getLine(line_id).onchain_view(storage=self.storage)

    def get_next_line_id(self):
        return self.pool.getNextLineId().onchain_view(storage=self.storage)

    def get_entry(self, entry_id):
        return self.pool.getEntry(entry_id).onchain_view(storage=self.storage)

    def get_next_entry_id(self):
        return self.pool.getNextEntryId().onchain_view(storage=self.storage)

    def get_shares(self, provider):
        return self.pool.getShares(provider).onchain_view(
            storage=self.storage
        )

    def get_next_position_id(self):
        return self.pool.getNextPositionId().onchain_view(storage=self.storage)

    def get_claim(self, event_id, provider):
        key = {'eventId': event_id, 'provider': provider}
        return self.pool.getClaim(key).onchain_view(storage=self.storage)

    def get_active_events(self):
        return self.pool.getActiveEvents().onchain_view(storage=self.storage)

    def get_event(self, event_id):
        return self.pool.getEvent(event_id).onchain_view(storage=self.storage)

    def is_deposit_paused(self):
        return self.pool.isDepositPaused().onchain_view(storage=self.storage)

    def get_entry_lock_period(self):
        return self.pool.getEntryLockPeriod().onchain_view(
            storage=self.storage
        )

    def get_manager(self):
        return self.pool.getManager().onchain_view(storage=self.storage)

    def get_total_shares(self):
        return self.pool.getTotalShares().onchain_view(storage=self.storage)

    def get_state_values(self):
        return self.pool.getStateValues().onchain_view(storage=self.storage)

    def wait(self, wait_time=0):
        self.current_time += wait_time
