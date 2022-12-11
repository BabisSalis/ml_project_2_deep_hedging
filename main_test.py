import gym
import os
import argparse
import torch
import numpy as np

from gym import wrappers
from src.agent import DDPG
from src.network import MLP
from src.utils import NetkwargAction


###############################################
############# Parameter Setting ###############
###############################################

BATCH_SIZE = 32
N_EPISODE = 1000
DISC_RATE = 0.99
TRG_UPDATE = 100

env = gym.make("Pendulum-v1")

nHidden = 8
nState, nAction = env.observation_space.shape[0], env.action_space.shape[0]  # 3, 1
actor = MLP(nState, nHidden, nAction, "Tanh")
critic = MLP(nState + nAction, nHidden, nAction)

agent = DDPG(actor, critic, 1e-3, 1e-4, DISC_RATE, BATCH_SIZE)

if __name__ == "__main__":

    episode_rewards = []
    for episode in range(N_EPISODE):
        # reset state
        state, _ = env.reset()  # s_0
        total_reward = 0

        while True:
            # take action given state
            action = agent.act(state, 0.5)

            # take next step of the environment
            next_state, reward, done, _, _ = env.step(action)

            # record interaction between environment and the agent
            agent.store(state, action, reward, next_state, done)
            # env.render()

            total_reward += reward
            state = next_state
            agent.update()

            if done:
                break

        episode_rewards.append(total_reward)
        print(f"Episode Num {episode}, total_reward = {total_reward}")

        if episode % TRG_UPDATE == 0:  # update target network
            agent.polyak_update()
