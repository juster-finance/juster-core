from executors import LoopExecutor


class EventLoopExecutor(LoopExecutor):
    """ Executes self.execute each period seconds for given events using data
        from dipdup and communication with contract using pytezos, creates
        transactions that pushed into operations queue """

    def __init__(
            self,
            config,
            contract,
            operations_queue,
            dd_client,
        ):
        """ Creates new EventLoopExecutor,
        - config: configuration object
        - contract: juster contract, pytezos instance
        - operations_queue: queue object where transactions should go
        - dd_client: JusterDipDupClient instance
        - period: time in seconds used to sleep before executor re runned
        """

        super().__init__(config)

        self.contract = contract
        self.operations_queue = operations_queue
        self.dd_client = dd_client


    def is_event_exist(self, event_id):
        """ Return True if given event_id exist in self.contract """

        # Testing that event exist:
        try:
            self.contract.storage['events'][event_id]()
        except KeyError as e:
            self.logger.error(f'Catched error in transaction emulation test:')
            self.logger.error(f'Event ID: {event_id} is not found')
            self.logger.error(f'WARNING: ignoring this transaction')
            return False

        return True


    def check_transaction(self, transaction):
        """ Checks that transactions is possible to be signed """

        try:
            transaction.autofill().sign()
        # TODO: need to limit exception types to RPC errors
        # pytezos.rpc.node.RpcError
        # if there are 'proto.009-PsFLoren.contract.counter_in_the_past' in
        #    the error text, need to return transaction to the queue

        except Exception as e:
            self.logger.error(
                f'Catched error while checking transaction {transaction.contents}')
            self.logger.error(f'-- ERROR: {type(e)}, {str(e)}')
            self.logger.error('-- WARNING: Transaction is dropped')


    async def put_transaction(self, transaction):
        """ Check that transaction is correct and adds it to the queue """

        self.check_transaction(transaction)
        await self.operations_queue.put(transaction)

        self.logger.info(
            f'added transaction with content: {transaction.contents}')

