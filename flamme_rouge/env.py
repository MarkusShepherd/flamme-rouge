# -*- coding: utf-8 -*-

''' RL environment '''

from gym.spaces import Box, Discrete
from rl.core import Env, Processor


class FREnv(Env):
    ''' Flamme Rouge Environment '''

    reward_range = (0, 1)
    action_space = Discrete(10)
    observation_space = Box() # TODO

    def __init__(self, game) -> None:
        super(FREnv, self).__init__()
        self.game = game

    def step(self, action):
        pass # TODO

    def reset(self):
        self.game.reset()
        return self.observation

    def render(self, mode='human', close=False):
        print(str(self.game))

    def close(self):
        del self.game

    def seed(self, seed=None):
        pass # TODO

    def configure(self, *args, **kwargs):
        pass # TODO

    @property
    def observation(self):
        ''' game observation '''

        pass # TODO


class FRProcessor(Processor):
    ''' Flamme Rouge Processor '''

    # def process_step(self, observation, reward, done, info):
    #     return super().process_step(observation, reward, done, info)

    # def process_observation(self, observation):
    #     return super().process_observation(observation)

    # def process_reward(self, reward):
    #     return super().process_reward(reward)

    # def process_info(self, info):
    #     return super().process_info(info)

    # def process_action(self, action):
    #     return super().process_action(action)

    # def process_state_batch(self, batch):
    #     return super().process_state_batch(batch)
