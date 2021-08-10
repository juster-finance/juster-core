from executors import LoopExecutor
from utility import repeat_until_succeed


class BulkSender(LoopExecutor):
    """ Listens to the queue and packs all new operations to the bulk,
        signs and sends the transaction
    """

    def __init__(self, config, client, operations_queue):
        super().__init__(config)
        self.client = client
        self.operations_queue = operations_queue


    async def sign(self, max_operations=None):

        max_operations = max_operations or self.config.MAX_OPERATIONS_IN_BULK

        # TODO: check if ready to sign
        # ? await self.is_ready_to_sign()

        # TODO: check balance is enough?

        operations = []
        while (not self.operations_queue.empty()
               and (len(operations) < max_operations)):
            operations.append(await self.operations_queue.get())

        if not len(operations):
            return

        try:
            self.logger.info(f'making bulk of {len(operations)} operations')
            result = self.client.bulk(*operations).autofill().sign().inject()
            self.logger.info(f'signed, result: {result}')
            return result

        except Exception as e:
            self.logger.error(f'catched {type(e)} in sign: {str(e)}')
            # TODO: here I need to classify error and if it was RPC error:
            # return operations back to the queue, if not: raise this e

            # TODO: change this list to RPCError, MichelsonError and other
            # possible errors that required to cancel transaction and return
            # operation to the queue

            for operation in operations:
                await self.operations_queue.put(operation)

            # catched:
            # -- requests.exceptions.ConnectionError
            # -- pytezos.rpc.errors.MichelsonError
            #       error str contains: proto.009-PsFLoren.michelson_v1.script_rejected
            # -- pytezos.rpc.node.RpcError
            # -- OSError
            #       error str contains: Could not find a suitable TLS CA certificate
            # TODO: analyze logs and find all this catched errors


    async def is_ready_to_sign(self, sleep_time=90):
        """ Waits while client would be possible to sign transaction
            - simple solution is just timer, better would be to reduce 
                this sleep_time value and somehow ask RPC if key is freed
        """

        return await asyncio.sleep(sleep_time)


    async def execute(self):
        return await repeat_until_succeed(self.sign)

