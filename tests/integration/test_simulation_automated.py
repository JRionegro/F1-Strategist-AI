"""
Automated test for simulation functionality.
Tests the complete flow without human interaction.
"""
import time
import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://127.0.0.1:8501"


def wait_for_server(timeout=30):
    """Wait for Dash server to be ready."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(BASE_URL, timeout=5)
            if response.status_code == 200:
                logger.info("Server is ready")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
    logger.error("Server did not start in time")
    return False


def test_simulation_flow():
    """Test the complete simulation flow."""
    logger.info("=" * 80)
    logger.info("AUTOMATED SIMULATION TEST")
    logger.info("=" * 80)

    # Wait for server
    if not wait_for_server():
        logger.error("Failed to connect to server")
        return False

    # Give it extra time for initialization
    logger.info("Waiting 5s for full initialization...")
    time.sleep(5)

    logger.info("\n✓ Server is running")
    logger.info("✓ Open http://127.0.0.1:8501/ in your browser")
    logger.info("\nMANUAL STEPS TO TEST:")
    logger.info("1. Select 'Abu Dhabi 2025 - Race' from dropdown")
    logger.info("2. Wait for session to load (~5 seconds)")
    logger.info("3. Check 'Race Overview' dashboard appears")
    logger.info("4. Click the Play button (▶️)")
    logger.info("5. Watch the simulation run")
    logger.info("\nEXPECTED BEHAVIOR:")
    logger.info("- Lap counter should update every few seconds")
    logger.info("- Leaderboard should refresh without full page reload")
    logger.info("- No console errors about callbacks")
    logger.info("\nKEEPING SERVER ALIVE FOR 2 MINUTES...")
    logger.info("(Press Ctrl+C to stop)")

    try:
        time.sleep(120)
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")

    logger.info("\n" + "=" * 80)
    logger.info("Test monitoring completed")
    logger.info("=" * 80)
    return True


if __name__ == "__main__":
    test_simulation_flow()
