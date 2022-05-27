import jax
import jax.numpy as jnp
from jax import lax
from gymnax.environments import environment, spaces
from typing import Tuple
import chex
from flax import struct


@struct.dataclass
class EnvState:
    rewards: chex.Array
    total_regret: float
    time: int


@struct.dataclass
class EnvParams:
    optimal_return: float = 1.0
    max_steps_in_episode: int = 100


class SimpleBandit(environment.Environment):
    """
    JAX Compatible version of DiscountingChain bsuite environment. Source:
    github.com/deepmind/bsuite/blob/master/bsuite/environments/bandit.py
    """

    def __init__(self, num_actions: int = 11):
        super().__init__()
        self.num_actions = num_actions

    @property
    def default_params(self) -> EnvParams:
        # Default environment parameters
        return EnvParams()

    def step_env(
        self, key: chex.PRNGKey, state: EnvState, action: int, params: EnvParams
    ) -> Tuple[chex.Array, EnvState, float, bool, dict]:
        """Perform single timestep state transition."""
        reward = state.rewards[action]
        state = EnvState(
            state.rewards,
            state.total_regret + params.optimal_return - reward,
            state.time + 1,
        )

        # Check game condition & no. steps for termination condition
        done = self.is_terminal(state, params)
        info = {"discount": self.discount(state, params)}
        return (
            lax.stop_gradient(self.get_obs(state)),
            lax.stop_gradient(state),
            reward,
            done,
            info,
        )

    def reset_env(
        self, key: chex.PRNGKey, params: EnvParams
    ) -> Tuple[chex.Array, dict]:
        """Reset environment state by sampling initial position."""
        action_mask = jax.random.choice(
            key,
            jnp.arange(self.num_actions),
            shape=(self.num_actions,),
            replace=False,
        )
        rewards = jnp.linspace(0, 1, self.num_actions)[action_mask]

        state = EnvState(rewards, 0.0, 0)
        return self.get_obs(state), state

    def get_obs(self, state: EnvState) -> chex.Array:
        """Return observation from raw state trafo."""
        return jnp.ones(shape=(1, 1), dtype=jnp.float32)

    def is_terminal(self, state: EnvState, params: EnvParams) -> bool:
        """Check whether state is terminal."""
        # Episode always terminates after single step - Do not reset though!
        return True

    @property
    def name(self) -> str:
        """Environment name."""
        return "SimpleBandit-bsuite"

    @property
    def action_space(self) -> spaces.Discrete:
        """Action space of the environment."""
        return spaces.Discrete(self.num_actions)

    def observation_space(self, params: EnvParams) -> spaces.Box:
        """Observation space of the environment."""
        return spaces.Box(1, 1, (1, 1))

    def state_space(self, params: EnvParams) -> spaces.Dict:
        """State space of the environment."""
        return spaces.Dict(
            {
                "rewards": spaces.Box(0, 1, (self.num_actions,)),
                "total_regret": spaces.Box(0, params.max_steps_in_episode, ()),
                "time": spaces.Discrete(params.max_steps_in_episode),
            }
        )
