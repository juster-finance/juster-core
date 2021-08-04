from executors import LoopExecutor
from config import EXECUTOR_UPDATE_PERIOD
import logging


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
        self.logger = logging.getLogger(__name__)
        self.dd_client = dd_client

