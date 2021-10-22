class Agreement:
    def __init__(self, user, pool, reward):
        self.user = user
        self.pool = pool
        self.reward = reward

    def to_dict(self):
        return {
            'user': self.user,
            'pool': self.pool,
            'reward': self.reward
        }
