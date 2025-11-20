"""Configuration management for Soomgo Agent."""

import yaml
from pathlib import Path
from typing import Optional, Dict, Any


def load_config(env) -> Dict[str, Any]:
    """Load configuration from config file.

    Args:
        env: Environment object with config_file path

    Returns:
        Configuration dictionary
    """
    if not env.config_file.exists():
        return {}

    try:
        with open(env.config_file, 'r') as f:
            config = yaml.safe_load(f) or {}
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}


def save_config(env, config: Dict[str, Any]) -> bool:
    """Save configuration to config file.

    Args:
        env: Environment object with config_file path
        config: Configuration dictionary to save

    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure config directory exists
        env.config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(env.config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False


def get_api_key(env) -> Optional[str]:
    """Get OpenAI API key from config.

    Args:
        env: Environment object

    Returns:
        API key string or None if not configured
    """
    config = load_config(env)
    return config.get('openai_api_key')


def set_api_key(env, api_key: str) -> bool:
    """Set OpenAI API key in config.

    Args:
        env: Environment object
        api_key: API key to save

    Returns:
        True if successful, False otherwise
    """
    config = load_config(env)
    config['openai_api_key'] = api_key
    return save_config(env, config)


def create_default_config(env) -> Dict[str, Any]:
    """Create default configuration.

    Args:
        env: Environment object

    Returns:
        Default configuration dictionary
    """
    default_config = {
        'version': '0.1.0',
        'agent': {
            'model': 'gpt-4o-mini',
            'temperature': 0.85,
            'max_tokens': 300,
        },
        'knowledge': {
            'similarity_threshold': 0.4,
            'top_k': 3,
        },
    }

    save_config(env, default_config)
    return default_config


def is_configured(env) -> bool:
    """Check if the app is configured with required settings.

    Args:
        env: Environment object

    Returns:
        True if configured (has API key), False otherwise
    """
    api_key = get_api_key(env)
    return api_key is not None and len(api_key) > 0
