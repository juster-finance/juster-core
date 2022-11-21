from typing import Callable
from typing import Optional
from typing import TypeVar

from requests.exceptions import ConnectTimeout

SomeReturn = TypeVar('SomeReturn')


class TooManyAttempts(Exception):
    pass


def try_multiple_times(
    unstable_func: Callable[[], SomeReturn],
    suppress: Optional[tuple] = None,
    max_attempts=25,
) -> SomeReturn:
    """Runs given function multiple times if it fails with allowed exceptions
    :param unstable_func: callable function
    :param suppress: tuple of suppressed exceptions
    :param max_attempts: maximum attempts before failing to run
    :raises: TooManyAttempts if failed to run max_attempts times
    """

    attempt: int = 0
    suppress = suppress or (ConnectTimeout, StopIteration)

    while attempt < max_attempts:
        try:
            attempt += 1
            return unstable_func()
        except suppress as e:
            print(f'failed with type(e), attempt #{attempt}, error: {str(e)}')

    raise TooManyAttempts('Failed {max_attempts} times')


def to_hex(string: str) -> str:
    """Converts given string to bytes and then hex"""
    return string.encode().hex()
