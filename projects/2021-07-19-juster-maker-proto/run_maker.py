""" CLI tool that running Juster Maker """

import config
import asyncio
from juster_maker import JusterMaker
from event_lines import EventLines



def generate_event_lines():
    """ Recreating event_lines.json if this is required """

    event_lines = EventLines()
    event_lines.generate_new()
    event_lines.save(EVENT_LINES_PARAMS_FN)


async def run_maker():
    maker = JusterMaker()
    maker.create_executors()
    await maker.run()


if __name__ == '__main__':
    asyncio.run(run_maker())

