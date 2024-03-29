# TODO: your agent here!
import numpy as np
import random

from collections import namedtuple, deque
from keras import layers, models, optimizers
from keras import backend as K

class ReplayBuffer:
    
    def __init__(self, buffer_size, batch_size): 
        '''
        initialize objects - buffer_size, batch_size
        Sets the memory, batch_size and experience
        '''
        self.memory = deque(maxlen=buffer_size)
        self.batch_size = batch_size
        self.experience = namedtuple("Experience", field_names=["state", "action", "reward", "next_state", "done"])
        
    def add(self, state, action, reward, next_state, done): 
        '''
        Add to memory from the experience
        '''
        e = self.experience(state, action, reward, next_state, done)
        self.memory.append(e)
    
    def sample(self, batch_size=64): 
        '''
        returns random memory samples
        '''
        return random.sample(self.memory, k=self.batch_size)
    
    def __len__(self): 
        '''Returns size of memory'''
        return len(self.memory)
    
class OUNoise:
       
    def __init__(self, size, mu, theta, sigma): 
        '''
        Initailize param and noise process
        '''
        self.mu = mu * np.ones(size)
        self.theta = theta
        self.sigma = sigma
        self.reset()
        
    def reset(self): 
        '''reset internal state to mean'''
        self.state = self.mu
        
    def sample(self): 
        '''update internal state and return noise sample'''
        x = self.state
        d = self.theta * (self.mu - x) + self.sigma * np.random.randn(len(x))
        self.state = x + d
        return self.state
    
class DDPG():
    """Reinforcement Learning agent that learns using DDPG."""
    def __init__(self, task):
        self.task = task
        self.state_size = task.state_size
        self.action_size = task.action_size
        self.action_low = task.action_low
        self.action_high = task.action_high

        # Actor (Policy) Model
        self.actor_local = Actor(self.state_size, self.action_size, self.action_low, self.action_high)
        self.actor_target = Actor(self.state_size, self.action_size, self.action_low, self.action_high)

        # Critic (Value) Model
        self.critic_local = Critic(self.state_size, self.action_size)
        self.critic_target = Critic(self.state_size, self.action_size)

        # Initialize target model parameters with local model parameters
        self.critic_target.model.set_weights(self.critic_local.model.get_weights())
        self.actor_target.model.set_weights(self.actor_local.model.get_weights())

        # Noise process
        self.exploration_mu = 0
        self.exploration_theta = 0.15
        self.exploration_sigma = 0.2
        self.noise = OUNoise(self.action_size, self.exploration_mu, self.exploration_theta, self.exploration_sigma)

        # Replay memory
        self.buffer_size = 100000
        self.batch_size = 64
        self.memory = ReplayBuffer(self.buffer_size, self.batch_size)

        # Algorithm parameters
        self.gamma = 0.99  # discount factor
        self.tau = 0.01  # for soft update of target parameters

    def reset_episode(self):
        self.noise.reset()
        state = self.task.reset()
        self.last_state = state
        return state

    def step(self, action, reward, next_state, done):
         # Save experience / reward
        self.memory.add(self.last_state, action, reward, next_state, done)

        # Learn, if enough samples are available in memory
        if len(self.memory) > self.batch_size:
            experiences = self.memory.sample()
            self.learn(experiences)

        # Roll over last state and action
        self.last_state = next_state

    def act(self, states):
        """Returns actions for given state(s) as per current policy."""
        state = np.reshape(states, [-1, self.state_size])
        action = self.actor_local.model.predict(state)[0]
        return list(action + self.noise.sample())  # add some noise for exploration

    def learn(self, experiences):
        """Update policy and value parameters using given batch of experience tuples."""
        # Convert experience tuples to separate arrays for each element (states, actions, rewards, etc.)
        states = np.vstack([e.state for e in experiences if e is not None])
        actions = np.array([e.action for e in experiences if e is not None]).astype(np.float32).reshape(-1, self.action_size)
        rewards = np.array([e.reward for e in experiences if e is not None]).astype(np.float32).reshape(-1, 1)
        dones = np.array([e.done for e in experiences if e is not None]).astype(np.uint8).reshape(-1, 1)
        next_states = np.vstack([e.next_state for e in experiences if e is not None])

        # Get predicted next-state actions and Q values from target models
        #     Q_targets_next = critic_target(next_state, actor_target(next_state))
        actions_next = self.actor_target.model.predict_on_batch(next_states)
        Q_targets_next = self.critic_target.model.predict_on_batch([next_states, actions_next])

        # Compute Q targets for current states and train critic model (local)
        Q_targets = rewards + self.gamma * Q_targets_next * (1 - dones)
        self.critic_local.model.train_on_batch(x=[states, actions], y=Q_targets)

        # Train actor model (local)
        action_gradients = np.reshape(self.critic_local.get_action_gradients([states, actions, 0]), (-1, self.action_size))
        self.actor_local.train_fn([states, action_gradients, 1])  # custom training function

        # Soft-update target models
        self.soft_update(self.critic_local.model, self.critic_target.model)
        self.soft_update(self.actor_local.model, self.actor_target.model)   

    def soft_update(self, local_model, target_model):
        """Soft update model parameters."""
        local_weights = np.array(local_model.get_weights())
        target_weights = np.array(target_model.get_weights())

        assert len(local_weights) == len(target_weights), "Local and target model parameters must have the same size"

        new_weights = self.tau * local_weights + (1 - self.tau) * target_weights
        target_model.set_weights(new_weights)
 
    
    
class Actor():
    
    def __init__(self, state_size, action_size, action_low, action_high): #initalize param
        self.state_size = state_size
        self.action_size = action_size
        self.action_low = action_low
        self.action_high = action_high
        self.action_range = self.action_high - self.action_low
        self.dropout_rate = 0.5
        self.learning_rate = 0.00147
        self.build_model()
   
    def build_model(self):
         #input layer
        states = layers.Input(shape=(self.state_size,), name = 'states')
        
        #hidden layers
        net = layers.Dense(units=32, activation='relu')(states)
        net = layers.BatchNormalization()(net)
 
        net = layers.Dense(units=64, activation='relu')(net)
        net = layers.BatchNormalization()(net)
        net = layers.Dropout(self.dropout_rate)(net)
        
        net = layers.Dense(units=32, activation='relu')(net)
        net = layers.BatchNormalization()(net)
        
        
        #output layer
        raw_actions = layers.Dense(units = self.action_size, activation = 'sigmoid', name = 'raw_actions')(net)
        
        actions = layers.Lambda(lambda x: (x* self.action_range) + self.action_low, name = 'actions')(raw_actions)
        
        #keras model
        self.model = models.Model(inputs=states, outputs=actions)
        
        #loss function using action value gradients
        action_gradients = layers.Input(shape=(self.action_size,))
        loss = K.mean(-action_gradients * actions)
        
        #optimizer and training
        optimizer = optimizers.Adam(lr=self.learning_rate)
        updates_op = optimizer.get_updates(params=self.model.trainable_weights, loss=loss)
        self.train_fn = K.function(
            inputs = [self.model.input, action_gradients, K.learning_phase()], 
            outputs=[], updates=updates_op)
        
class Critic:
    
    def __init__(self, state_size, action_size): #initalize and build model
        self.state_size = state_size
        self.action_size = action_size
        self.dropout_rate = 0.5
        self.learning_rate = 0.00147
        self.build_model()
    
    def build_model(self):
        #input layers
        states = layers.Input(shape=(self.state_size,), name = 'states')
        actions = layers.Input(shape=(self.action_size,), name = 'actions')
        
        #hidden layers for states
        net_states = layers.Dense(units=32, activation='relu')(states)
        net_states = layers.BatchNormalization()(net_states)

        net_states = layers.Dense(units=64, activation='relu')(net_states)
        net_states = layers.BatchNormalization()(net_states)
        net_states = layers.Dropout(self.dropout_rate)(net_states)
        
        net_states = layers.Dense(units=32, activation='relu')(states)
        net_states = layers.BatchNormalization()(net_states)
        
        #hidden layers for actions
        net_actions = layers.Dense(units=32, activation='relu')(actions)
        net_actions = layers.BatchNormalization()(net_actions)
     
        net_actions = layers.Dense(units=64, activation='relu')(net_actions)
        net_actions = layers.BatchNormalization()(net_actions)       
        net_actions = layers.Dropout(self.dropout_rate)(net_actions)
        
        net_actions = layers.Dense(units=32, activation='relu')(actions)
        net_actions = layers.BatchNormalization()(net_actions)
        
        #combine
        net = layers.Add()([net_states, net_actions])
        net = layers.Activation('relu')(net)
        
        #output layer
        Q_values = layers.Dense(units=1, name='q_values')(net)
        
        #keras model
        self.model = models.Model(inputs=[states, actions], outputs=Q_values)
        
        #optimizer and training
        optimizer = optimizers.Adam(lr=self.learning_rate)
        self.model.compile(optimizer=optimizer, loss='mse')
        
        #compute and fetch action gradient
        action_gradients = K.gradients(Q_values, actions)
        self.get_action_gradients = K.function(
            inputs=[*self.model.input, K.learning_phase()],
            outputs=action_gradients)