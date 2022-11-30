import gym
import os
import argparse
import torch

from gym import envs
from src.agent import DDPG
from src.network import MLP, CNN
from src.utils import NetkwargAction


networks = {"mlp": MLP, "cnn": CNN}

if __name__ == "__main__":
    # initialize ArgumentParser class of argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--net", help="type of network", default="mlp", type=str)
    parser.add_argument("--gamma", help="discount rate", default=0.99, type=float)
    parser.add_argument("--epsilon", help="exploration coeff", default=0.05, type=float)
    parser.add_argument("--n_episode", help="number of episodes", default=100, type=int)
    parser.add_argument("--sigma", help="sigma", default=0.1, type=float)

    parser.add_argument(
        "--batch_size", help="batch size for update", default=100, type=int
    )
    parser.add_argument(
        "--n_maxstep", help="maximum steps per episode", default=500, type=int
    )
    parser.add_argument(
        "--learning_rate", help="learning rate", default=1e-3, type=float
    )
    parser.add_argument(
        "--netkwargs",
        help="network keyword arguments",
        nargs="*",
        action=NetkwargAction,
    )

    # read the arguments from the command line
    args = parser.parse_args()

    # set up the environment and agent
    env = gym.make(args.env)
    actor = networks[args.net](dim_in, dim_hidden, dim_out)
    critic = networks[args.net](dim_in, dim_hidden, dim_out)
    agent = DDPG(
        env, actor, critic, args.learning_rate, args.gamma, args.sigma, args.batch_size
    )

    batch_reward_average = 0
    for episode in range(args.n_episode):
        # reset state to S_0
        state = env.reset()
        total_reward = 0

        for t in range(args.n_maxstep):
            # take action given state
            action = agent.act(state)

            # take next step of the environment
            next_state, reward, done, _ = env.step(action)

            # record interaction between environment and the agent
            agent.store(state, action, reward, next_state, done)
            env.render()
            total_reward += reward
            state = next_state

            if done:
                break

        agent.update()
        batch_reward_average += total_reward
        total_reward = 0

        if episode % 100 == 0:
            batch_reward_average = batch_reward_average / 100
            solved = batch_reward_average > 195.0
            print(
                f"Episode Batch {episode//100}, total_reward: {batch_reward_average}, solved: {solved}"
            )

            if solved:
                print(
                    f"solved!! at Episode Batch {episode//100}, total_reward: {batch_reward_average}"
                )
                break
            batch_reward_average = 0