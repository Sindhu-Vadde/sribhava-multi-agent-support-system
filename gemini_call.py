import random
import sys
import time

from google.genai import errors

# Errors that usually clear up if we wait a moment: quota/rate limit (429) and Gemini being busy or down (5xx).
RETRYABLE_CODES = (429, 500, 503, 504)


def generate_with_retry(client, model, contents, config, max_attempts=4, base_delay=2.0, sleep=time.sleep):
    """Calls Gemini, and if it says 'busy' or 'quota', waits a little longer each time and tries again."""
    for attempt in range(1, max_attempts + 1):
        try:
            return client.models.generate_content(model=model, contents=contents, config=config)
        except errors.APIError as e:
            if e.code not in RETRYABLE_CODES or attempt == max_attempts:
                raise
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
            print(f"Gemini error {e.code}, retrying in {delay:.0f}s (attempt {attempt} of {max_attempts})",
                  file=sys.stderr)
            sleep(delay)