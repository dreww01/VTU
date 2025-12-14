import logging
import requests
from django.conf import settings
from transactions.providers.exceptions import VTPassError

logger = logging.getLogger('transactions')

def check_and_get_transaction_status(reference):
    """
    Check if transaction exists on VTPass and get its status.
    Returns: 
        - "completed", "failed", or "pending" if transaction exists
        - None if transaction doesn't exist
    """
    url = f"{settings.VTPASS_BASE_URL}/api/requery"
    headers = {
        'api-key': settings.VTPASS_API_KEY,
        'public-key': settings.VTPASS_PUBLIC_KEY,
    }
    payload = {
        'request_id': reference
    }

    logger.debug(f"Checking VTPass for transaction: {reference}")
    logger.debug(f"URL: {url}")
    logger.debug(f"Headers: {headers}")
    logger.debug(f"Payload: {payload}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        logger.debug(f"Response status: {response.status_code}")
        logger.debug(f"Response body: {response.text}")
        
        # If transaction doesn't exist, VTPass returns 404
        if response.status_code == 404:
            logger.warning(f"Transaction {reference} not found on VTPass (404)")
            return None
        
        response.raise_for_status()
        data = response.json()

        logger.info(f"VTPass response for {reference}: {data}")

        # Check response structure
        if 'content' not in data or 'transactions' not in data['content']:
            logger.error(f"Unexpected VTPass response: {data}")
            raise VTPassError(f"Unexpected response format: {data}")

        transaction_data = data['content']['transactions']
        status = transaction_data.get('status', '').lower()

        # Map VTPass status to our app status
        if status in ['delivered', 'success']:
            return "completed"
        elif status in ['failed', 'reversed']:
            return "failed"
        else:
            return "pending"

    except requests.exceptions.Timeout:
        logger.error(f"Timeout checking VTPass for {reference}")
        raise VTPassError(f"VTPass API timeout for {reference}")
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error contacting VTPass for {reference}: {str(e)}")
        raise VTPassError(f"VTPass API error: {str(e)}")