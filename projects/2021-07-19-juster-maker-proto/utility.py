from datetime import datetime


async def repeat_until_succeed(
        func, allowed_exceptions=None, max_attempts=10, wait_after_fail=10):
    """ Runs func for multiple times if it was failed with any of the allowed
        exceptions """

    allowed_exceptions = allowed_exceptions or []

    for attempt in range(max_attempts):
        try:
            return await func()

        except Exception as e:
            if type(e) in allowed_exceptions:
                print(f'Ignoring error {type(e)}, {str(e)}')
                await asyncio.sleep(wait_after_fail)
            else:
                raise e


def date_to_timestamp(date, time_format='%Y-%m-%d %H:%M:%S'):
    """ Converts date to timestamp using by default
        '%Y-%m-%d %H:%M:%S' format """

    return datetime.strptime(date, time_format).timestamp()
