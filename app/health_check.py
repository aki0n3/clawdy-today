#!/usr/bin/env python3
"""
Health check script for OpenClaw Agent API
Tests the API with random tasks and logs results
"""

import requests
import json
import random
import time
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Setup logging
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "health_check.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "http://localhost:8000"
RANDOM_TASK_ENDPOINT = f"{API_BASE_URL}/task/send"
STREAM_ENDPOINT = f"{API_BASE_URL}/stream"

# Random intervals in seconds (30 minutes to 3 hours)
MIN_INTERVAL = 30 * 60  # 30 minutes
MAX_INTERVAL = 3 * 60 * 60  # 3 hours


def test_random_task():
    """Test /task/send endpoint with random task"""
    try:
        logger.info("Starting health check - Testing /task/send endpoint")
        
        start_time = time.time()
        response = requests.post(
            RANDOM_TASK_ENDPOINT,
            timeout=120,
            json={}
        )
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            logger.info(
                f"✓ Health check PASSED | "
                f"Status: {response.status_code} | "
                f"Model: {data.get('model')} | "
                f"Time: {elapsed_time:.2f}s | "
                f"Tokens: {data.get('input_tokens', 0)}/{data.get('output_tokens', 0)}"
            )
            return True
        else:
            logger.error(
                f"✗ Health check FAILED | "
                f"Status: {response.status_code} | "
                f"Response: {response.text[:200]}"
            )
            return False
            
    except requests.exceptions.Timeout:
        logger.error("✗ Health check FAILED | Timeout (120s)")
        return False
    except requests.exceptions.ConnectionError:
        logger.error("✗ Health check FAILED | Connection refused - Is the API running?")
        return False
    except Exception as e:
        logger.error(f"✗ Health check FAILED | {type(e).__name__}: {str(e)}")
        return False


def test_stream():
    """Test /stream endpoint"""
    try:
        logger.info("Testing /stream endpoint")
        
        response = requests.get(
            STREAM_ENDPOINT,
            timeout=30,
            stream=True
        )
        
        if response.status_code == 200:
            event_count = 0
            for line in response.iter_lines():
                if line and line.startswith(b"data: "):
                    event_count += 1
            
            logger.info(f"✓ Stream test PASSED | Events received: {event_count}")
            return True
        else:
            logger.error(f"✗ Stream test FAILED | Status: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"✗ Stream test FAILED | {type(e).__name__}: {str(e)}")
        return False


def run_health_check():
    """Run full health check"""
    logger.info("=" * 80)
    logger.info("Health check started")
    logger.info("=" * 80)
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "random_task": test_random_task(),
        "stream": test_stream()
    }
    
    if all(results.values()):
        logger.info("✓ All health checks PASSED")
        return True
    else:
        logger.error("✗ Some health checks FAILED")
        return False
    

def sleep_random():
    """Sleep for random interval between MIN_INTERVAL and MAX_INTERVAL"""
    interval = random.randint(MIN_INTERVAL, MAX_INTERVAL)
    minutes = interval / 60
    hours = minutes / 60
    logger.info(f"Sleeping for {hours:.1f} hours ({minutes:.0f} minutes) before next check")
    time.sleep(interval)


def daemon_mode():
    """Run as daemon with random intervals"""
    logger.info("Starting health check daemon")
    logger.info(f"Random interval: {MIN_INTERVAL/60:.0f}m - {MAX_INTERVAL/3600:.1f}h")
    
    try:
        while True:
            run_health_check()
            sleep_random()
    except KeyboardInterrupt:
        logger.info("Daemon stopped by user")


def main():
    parser = argparse.ArgumentParser(
        description="Health check for OpenClaw Agent API"
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as daemon with random intervals"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run health check once and exit"
    )
    parser.add_argument(
        "--stream-only",
        action="store_true",
        help="Test only stream endpoint"
    )
    parser.add_argument(
        "--task-only",
        action="store_true",
        help="Test only task endpoint"
    )
    
    args = parser.parse_args()
    
    if args.daemon:
        daemon_mode()
    elif args.once or (not args.daemon and not args.stream_only and not args.task_only):
        # Default: run once
        if args.task_only:
            test_random_task()
        elif args.stream_only:
            test_stream()
        else:
            run_health_check()
    elif args.stream_only:
        test_stream()
    elif args.task_only:
        test_random_task()


if __name__ == "__main__":
    main()
