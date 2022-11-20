from requests.exceptions import ConnectTimeout


def try_multiple_times(unstable_func, max_attempts=25):
    attempt = 0
    while attempt < max_attempts:
        try:
            attempt += 1
            return unstable_func()
        except ConnectTimeout as e:
            print(f'failed with ConnectionTimeout, attempt #{attempt}')
            pass
        except StopIteration as e:
            print(f'failed with StopIteration ({str(e)}), attempt #{attempt}')
            pass

    raise Exception('too many attempts')


def to_hex(string):
    return string.encode().hex()
