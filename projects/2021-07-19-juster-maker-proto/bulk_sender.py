from loop_executor import LoopExecutor
from utility import repeat_until_succeed


class BulkSender(LoopExecutor):
    """ Listens to the queue and packs all new operations to the bulk,
        signs and sends the transaction
    """

    def __init__(self, period, client, operations_queue):
        super().__init__(period)

        self.client = client
        self.operations_queue = operations_queue


    async def sign(self, max_operations=10):
        # TODO: check if ready to sign
        # ? await self.is_ready_to_sign()

        operations = []
        while (not self.operations_queue.empty()
               and (len(operations) < max_operations)):
            operations.append(await self.operations_queue.get())

        if not len(operations):
            return

        try:
            # TODO: logging instead of printing, add .json_payload() info and hahses
            print(f'making bulk of {len(operations)} operations')
            result = self.client.bulk(*operations).autofill().sign()
            print(f'signed, result hash: {result.hash()}')
            # TODO: add inject()
            return result

        except Exception as e:
            print(f'catched {type(e)} in sign: {str(e)}')
            # TODO: here I need to classify error and if it was RPC error: return
            # operations back to the queue, if not: raise this e
            import pdb; pdb.set_trace()
            raise e


    async def is_ready_to_sign(self, sleep_time=90):
        """ Waits while client would be possible to sign transaction
            - simple solution is just timer, better would be to reduce 
                this sleep_time value and somehow ask RPC if key is freed
        """

        return await asyncio.sleep(sleep_time)


    async def execute(self):
        return await repeat_until_succeed(self.sign)

