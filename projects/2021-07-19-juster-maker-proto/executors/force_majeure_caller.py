from executors import EventLoopExecutor
import time
import asyncio
from dateutil.parser import parse
from pytezos.michelson.micheline import MichelsonRuntimeError
from dateutil.parser import parse


def detect_failed_start(event, trigger_timestamp):
    """ Returns True if event was failed to be started before
        trigger_timestamp, so this is possible to run
        triggerForceMajeure for this event
    """

    have_no_started_time = event['measure_oracle_start_time'] is None
    bets_close_timestamp = event['bets_close_time'].timestamp()
    should_be_started = trigger_timestamp > bets_close_timestamp
    return have_no_started_time and should_be_started


def detect_failed_close(event, trigger_timestamp):
    """ Returns True if event was failed to be closed before
        trigger_timestamp, so this is possible to run
        triggerForceMajeure for this event
    """

    have_no_finished_time = event['closed_oracle_time'] is None
    close_timestamp = (
        event['bets_close_time'].timestamp()
        + event['measure_period']
    )
    should_be_closed = trigger_timestamp > close_timestamp
    return have_no_finished_time and should_be_closed


class ForceMajeureCaller(EventLoopExecutor):

    async def _make_trigger_force_majeure_transaction(self, event_id):

        operation = self.contract.triggerForceMajeure(event_id)
        transaction = operation.as_transaction()
        await self.put_transaction(transaction)


    async def query_open_event_times(self):
        """ TODO: rename me and add description """
        # TODO: there are potential problem if there would be
        # too many opened events (>100). Then this request may return
        # only valid unclosed events. Maybe need to do some sorting
        # by event_id ASC for example

        return await self.dd_client.make_query('open_event_times')


    async def trigger_force_majeures(self):

        events = await self.query_open_event_times()
        trigger_timestamp = time.time() - self.config.MAX_ALLOWED_MEASURE_LAG

        def detect_failed(event):
            return (
                detect_failed_start(event, trigger_timestamp)
                or detect_failed_close(event, trigger_timestamp)
            )

        events = [event for event in events if detect_failed(event)]

        # checking that there are no duplicates:
        assert len({event['id'] for event in events}) == len(events)

        # emitting transactions:
        for event in events:
            await self._make_trigger_force_majeure_transaction(event['id'])

        # TODO: is it good to have this 10 minutes wait?
        # feels that it is possible to have some kind of trigger to
        # continue (dipdup subscription?)
        await asyncio.sleep(600)


    async def execute(self):
        return await self.trigger_force_majeures()

