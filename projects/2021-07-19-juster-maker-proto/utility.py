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

