from os.path import join
from os import listdir
from pytezos import pytezos
from pprint import pprint


def load_key_filenames(directory):

    def make_key_name(fn):
        return fn.split('.')[0]

    filenames =  {
        make_key_name(fn): join(directory, fn)
        for fn in listdir(directory) if fn.lower().endswith('.json')
    }

    if not filenames:
        raise Exception(
            'Please add test keys into pytezos-jupyter-present/test-keys directory '
            + '(you can use https://faucet.tzalpha.net/')

    return filenames


class KeysManager:
    def __init__(self, settings):

        self.settings = settings
        self.key_filenames = load_key_filenames(settings['KEYS_DIRECTORY'])
        self.shell_url = settings['SHELL_URL']
        self.is_async_enabled = settings['IS_ASYNC_ENABLED']

        self.pytezos_instances = {
            key_name: pytezos.using(key=key_filename, shell=self.shell_url)
            for key_name, key_filename in self.key_filenames.items()
        }

        assert len(self.pytezos_instances)
        print(f'Successfully loaded {len(self.pytezos_instances)} pytezos keys:')
        [print(f'- {key_name}') for key_name in self.pytezos_instances]


    def activate_keys(self):
        """ Runs activate_account for each loaded key """

        for key_name, pt in self.pytezos_instances.items():
            try:
                pt.activate_account().autofill().sign().inject(_async=self.is_async_enabled)
                pt.reveal().autofill().sign().inject(_async=self.is_async_enabled)
            except Exception as e:
                print(f'Error: {type(e)}, "{e}"')
