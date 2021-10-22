class Lock:
    def __init__(self, user, win_for, win_against):
        self.user = user
        self.win_for = win_for
        self.win_against = win_against

    def to_dict(self):
        return {
            'user': self.user,
            'win_for': self.win_for,
            'win_against': self.win_against
        }

