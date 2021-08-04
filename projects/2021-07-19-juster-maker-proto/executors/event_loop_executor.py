from executors import LoopExecutor
from config import EXECUTOR_UPDATE_PERIOD


class EventLoopExecutor(LoopExecutor):
    """ Executes self.execute each period seconds for given events using data
        from dipdup and communication with contract using pytezos, creates
        transactions that pushed into operations queue """

    def __init__(
            self,
            contract,
            operations_queue,
            dd_client,
            period=EXECUTOR_UPDATE_PERIOD
        ):
        """ Creates new EventLoopExecutor,
        - contract: juster contract, pytezos instance
        - operations_queue: queue object where transactions should go
        - dd_client: JusterDipDupClient instance
        - period: time in seconds used to sleep before executor re runned
        """

        # TODO: rename period to update_period
        super().__init__(period)

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

