import os
import time
import functools
import yaml
from pathlib import Path
import logging

logger = logging.getLogger("cloud_auditor")

CONFIG_PATH = Path.home() / ".cloud_auditor.yaml"

DEFAULT_CONFIG = {
    "aws": {
        "regions": ["us-east-1", "us-west-2", "eu-west-1"],
        "cpu_threshold": 5.0,
        "days_threshold": 14,
    },
    "gcp": {
        "regions": ["us-central1", "us-east1", "europe-west1"],
        "cpu_threshold": 5.0,
        "days_threshold": 14,
    }
}

def load_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                return yaml.safe_load(f) or DEFAULT_CONFIG
        except Exception as e:
            logger.warning(f"Failed to load config from {CONFIG_PATH}: {e}. Using defaults.")
    return DEFAULT_CONFIG

def save_config(config):
    try:
        with open(CONFIG_PATH, "w") as f:
            yaml.safe_dump(config, f)
    except Exception as e:
        logger.error(f"Failed to save config to {CONFIG_PATH}: {e}")

def retry_on_rate_limit(max_retries=5, base_delay=2.0):
    """
    Decorator to retry cloud provider API calls when rate-limited.
    Handles AWS Throttling and GCP 429 ResourceExhausted errors.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            delay = base_delay
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    is_rate_limit = False
                    err_msg = str(e)
                    
                    # AWS rate limiting checks
                    if hasattr(e, "response") and isinstance(e.response, dict):
                        error_code = e.response.get("Error", {}).get("Code", "")
                        if error_code in ["RequestLimitExceeded", "Throttling", "ThrottlingException", "PriorRequestNotComplete"]:
                            is_rate_limit = True
                    
                    # GCP rate limiting checks
                    if "429" in err_msg or "rateLimitExceeded" in err_msg or "ResourceExhausted" in err_msg or "QuotaExceeded" in err_msg:
                        is_rate_limit = True
                    
                    if is_rate_limit and retries < max_retries:
                        retries += 1
                        logger.warning(f"Rate limit hit in {func.__name__}. Retrying in {delay:.1f}s ({retries}/{max_retries})...")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        raise e
        return wrapper
    return decorator
