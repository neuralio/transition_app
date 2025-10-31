"""
RL-02: PPO Training with REAL MLU Simulation + Results Logging

Saves training metrics and test results to text files for easy tracking.
"""

import argparse
from pathlib import Path
from datetime import datetime
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback
from mlu_env import MLU_Env


class MetricsLogger(BaseCallback):
    """Callback to log training metrics to text file."""

    def __init__(self, log_file: str, verbose=0):
        super().__init__(verbose)
        self.log_file = log_file

    def _on_step(self) -> bool:
        return True

    def _on_rollout_end(self) -> None:
        """Save metrics after each rollout."""
        with open(self.log_file, 'a') as f:
            f.write(f"\nIteration {self.num_timesteps}:\n")
            for key, value in self.logger.name_to_value.items():
                f.write(f"  {key}: {value}\n")


def train_rl02(
    data_path: str,
    scenario: str = "rcp45",
    total_timesteps: int = 50000,
    save_dir: str = "models/rl02",
    checkpoint_freq: int = 5000
):
    """Train PPO agent with MLU simulation and save results to text files."""

    print("="*60)
    print("RL-02: TRAINING MLU AGENT")
    print("="*60)
    print(f"Scenario: {scenario}")
    print(f"Total timesteps: {total_timesteps}")
    print()

    # Create save directory
    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)

    # Create training log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = save_path / f"training_log_{scenario}_{timestamp}.txt"

    with open(log_file, 'w') as f:
        f.write("="*60 + "\n")
        f.write("RL-02: TRAINING MLU AGENT\n")
        f.write("="*60 + "\n")
        f.write(f"Scenario: {scenario}\n")
        f.write(f"Total timesteps: {total_timesteps}\n")
        f.write(f"Started: {timestamp}\n")
        f.write("="*60 + "\n\n")

    # Initialize environment
    print("🔄 Creating MLU environment...")
    env = MLU_Env(
        data_path=data_path,
        scenario=scenario,
        start_year=2021,
        max_steps=50
    )

    # Check environment
    print("\n🔍 Checking environment...")
    try:
        check_env(env)
        print("✅ Environment check passed!")
    except Exception as e:
        print(f"❌ Environment check failed: {e}")
        return

    # Initialize PPO with better value function
    print("\n🤖 Initializing PPO agent...")
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        vf_coef=0.5,        # Increase value function weight
        ent_coef=0.01,      # Add exploration bonus
        max_grad_norm=0.5,  # Gradient clipping
        device='auto',      # Auto-select best device
        tensorboard_log=f"{save_dir}/tensorboard/"
    )

    # Setup callbacks
    checkpoint_callback = CheckpointCallback(
        save_freq=checkpoint_freq,
        save_path=str(save_path / "checkpoints"),
        name_prefix=f"rl02_{scenario}"
    )

    metrics_logger = MetricsLogger(log_file=str(log_file))

    # Train
    print(f"\n🚀 Training for {total_timesteps} timesteps...\n")

    model.learn(
        total_timesteps=total_timesteps,
        callback=[checkpoint_callback, metrics_logger],
        progress_bar=True
    )

    # Save model
    final_model_path = save_path / f"rl02_{scenario}_final.zip"
    model.save(str(final_model_path))
    print(f"\n✅ Model saved to: {final_model_path}")

    # Test agent
    print("\n🧪 Testing trained agent...\n")
    test_results = test_agent(model, env, n_episodes=3)

    # Save results
    results_file = save_path / f"results_{scenario}_{timestamp}.txt"
    with open(results_file, 'w') as f:
        f.write("="*60 + "\n")
        f.write(f"RL-02 RESULTS - {scenario.upper()}\n")
        f.write("="*60 + "\n\n")

        f.write("Configuration:\n")
        f.write(f"  Scenario: {scenario}\n")
        f.write(f"  Timesteps: {total_timesteps}\n")
        f.write(f"  Episode length: 50 years\n\n")

        f.write("Test Episodes (3 runs):\n\n")
        for i, result in enumerate(test_results, 1):
            f.write(f"Episode {i}:\n")
            f.write(f"  Total Reward: {result['reward']:.2f}\n")
            f.write(f"  Avg Income: {result['avg_income']:.2f}€\n")
            f.write(f"  Actions: WHEAT={result['actions'][0]}, MAIZE={result['actions'][1]}, SOLAR={result['actions'][2]}\n\n")

        # Averages
        avg_reward = sum(r['reward'] for r in test_results) / 3
        avg_income = sum(r['avg_income'] for r in test_results) / 3

        f.write("Averages:\n")
        f.write(f"  Reward: {avg_reward:.2f}\n")
        f.write(f"  Income: {avg_income:.2f}€\n\n")

        f.write(f"Model: {final_model_path}\n")
        f.write(f"TensorBoard: {save_dir}/tensorboard/\n")

    print(f"\n📄 Results saved to: {results_file}")
    print(f"\nView TensorBoard:")
    print(f"  tensorboard --logdir={save_dir}/tensorboard/")

    return model


def test_agent(model, env, n_episodes: int = 3):
    """Test trained agent on different parcels within Thessaloniki."""
    print(f"Testing {n_episodes} episodes with randomized parcel locations...")
    results = []

    for episode in range(n_episodes):
        # Randomize parcel location to test generalization
        obs, info = env.reset(options={'randomize_location': True})
        episode_reward = 0
        actions_taken = []
        incomes = []

        print(f"  Episode {episode+1}: Testing parcel at ({info['parcel_lat']:.3f}, {info['parcel_lon']:.3f})")

        for step in range(50):
            action, _states = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)

            episode_reward += reward
            actions_taken.append(int(action))
            incomes.append(info['income'])

            if terminated or truncated:
                break

        # Count actions
        action_counts = {0: 0, 1: 0, 2: 0}
        for a in actions_taken:
            action_counts[int(a)] += 1

        avg_income = sum(incomes) / len(incomes) if incomes else 0

        result = {
            'reward': episode_reward,
            'avg_income': avg_income,
            'actions': (action_counts[0], action_counts[1], action_counts[2]),
            'parcel_lat': info.get('parcel_lat', 0),
            'parcel_lon': info.get('parcel_lon', 0)
        }
        results.append(result)

        print(f"    → Reward={episode_reward:.2f}, Income={avg_income:.2f}€, "
              f"WHEAT={action_counts[0]}, MAIZE={action_counts[1]}, SOLAR={action_counts[2]}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train RL-02 with REAL MLU")
    parser.add_argument("--data-path", type=str,
                       default="/app/data")
    parser.add_argument("--scenario", type=str, default="rcp45",
                       choices=["rcp26", "rcp45", "rcp85"])
    parser.add_argument("--timesteps", type=int, default=50000)
    parser.add_argument("--save-dir", type=str, default="models/rl02")
    parser.add_argument("--checkpoint-freq", type=int, default=5000)

    args = parser.parse_args()

    train_rl02(
        data_path=args.data_path,
        scenario=args.scenario,
        total_timesteps=args.timesteps,
        save_dir=args.save_dir,
        checkpoint_freq=args.checkpoint_freq
    )
