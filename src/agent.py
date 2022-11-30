import numpy as np
import torch
import torch.optim as optim
from torch.distributions import Normal

from abc import ABCMeta, abstractmethod
from .buffer import ExpReplay
from copy import deepcopy
from collections import namedtuple


class Algorithm(metaclass=ABCMeta):
    """
    Author: Kibeom

    Constructs an abstract based class Algorithm.
    This will be the main bone of all Reinforcement Learning algorithms.
    This class gives a clear structure of what needs to be implemented for all reinforcement algorithm in general.
    If there is other extra methods to be specified, child class will inherit the existing methods as well as
    add new methods to it.
    """

    def __init__(self, env, disc_rate, learning_rate):
        self.env = env
        self.gamma = disc_rate
        self.lr = learning_rate

    @abstractmethod
    def act(self):
        pass

    @abstractmethod
    def store(self):
        pass

    @abstractmethod
    def reset(self):
        pass

    @abstractmethod
    def update(self):
        pass


class DDPG(Algorithm):
    def __init__(self, Actor, Critic, actor_lr, critic_lr, disc_rate, batch_size):
        """
        Author: Kibeom

        Need to write docstring
        :param env: openai gym environment.
        :param Net: neural network class from pytorch module.
        :param learning_rate: learning rate of optimizer.
        :param disc_rate: discount rate used to calculate return G
        """

        self.tau = 0.05
        self.gamma = disc_rate
        self.batch_size = batch_size
        self.transition = namedtuple(
            "Transition",
            ("state", "action", "reward", "next_state", "done"),
        )
        self.buffer = ExpReplay(10000, self.transition)
        
        # define actor and critic ANN.
        self.actor  = Actor
        self.critic = Critic

        # define optimizer for Actor and Critic network
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=actor_lr)
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=critic_lr)

        # define target network needed for DDPG optimization
        self.actor_target = deepcopy(self.actor)
        self.critic_target = deepcopy(self.critic)

    def reset(self):
        self.buffer.clear()

    def store(self, *args):
        self.buffer.store(*args)

    def act(self, state, sigma=0.5):
        """
        We use policy function to find the deterministic action instead of distributions
        which is parametrized by distribution parameters learned from the policy.

        Here, state input prompts policy network to output a single or multiple-dim
        actions.
        :param state:
        :return:
        """
        x = torch.tensor(state.astype(np.float32))
        action = self.actor.forward(x)
        noise = Normal(torch.tensor([0.0]), torch.tensor([sigma])).sample()
        return torch.clip(action + noise, -2.0, 2.0).detach().numpy()

    def polyak_update(self):
        # Update the frozen target models
        for trg_param, src_param in zip(
            list(self.critic_target.parameters()), list(self.critic.parameters())
        ):
            trg_param = trg_param * (1.0 - self.tau) + src_param * self.tau

        for trg_param, src_param in zip(
            list(self.actor_target.parameters()), list(self.actor.parameters())
        ):
            trg_param = trg_param * (1.0 - self.tau) + src_param * self.tau

    def update(self):
        # calculate return of all times in the episode
        if self.buffer.len() < self.batch_size:
            return

        transitions = self.buffer.sample(self.batch_size)
        batch = self.transition(*zip(*transitions))

        # extract variables from sampled batch.
        states = torch.tensor(batch.state)
        actions = torch.tensor(batch.action)
        rewards = torch.tensor(batch.reward)
        dones = torch.tensor(batch.done).long()
        next_states = torch.tensor(batch.next_state)
        next_actions = self.actor_target(next_states)

        # compute target
        y = rewards + self.gamma * (1 - dones) * self.critic_target(
            torch.hstack((next_states, next_actions))
        )
        advantage = self.critic(torch.hstack([states, actions])) - y.detach()
        critic_loss = advantage.pow(2).mean()

        # Optimize the critic
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        self.critic_optimizer.step()

        # Get actor loss
        actor_loss = -self.critic(torch.hstack([states, self.actor(states)])).mean()

        # Optimize the actor
        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        self.actor_optimizer.step()

    def save(self, filename):
        torch.save(self.critic.state_dict(), filename + "_critic")
        torch.save(self.critic_optimizer.state_dict(), filename + "_critic_hyp_params")

        torch.save(self.actor.state_dict(), filename + "_actor")
        torch.save(self.actor_optimizer.state_dict(), filename + "_actor_hyp_params")

    def load(self, filename):
        self.critic.load_state_dict(torch.load(filename + "_critic"))
        self.critic_optimizer.load_state_dict(
            torch.load(filename + "_critic_hyp_params")
        )

        self.actor.load_state_dict(torch.load(filename + "_actor"))
        self.actor_optimizer.load_state_dict(torch.load(filename + "_actor_hyp_params"))