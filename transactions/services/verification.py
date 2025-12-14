import logging
from datetime import timedelta
from django.utils import timezone
from transactions.models import Transaction
from transactions.services.vtu_service import check_and_get_transaction_status
from transactions.providers.exceptions import VTPassError

logger = logging.getLogger('transactions')

def recheck_pending_vtu(max_age_minutes=10):
    """
    Recheck pending VTU transactions that are older than max_age_minutes.
    
    Logic:
    1. If transaction doesn't exist on VTPass -> Mark as FAILED
    2. If transaction exists on VTPass -> Update status based on VTPass status
    """
    stats = {
        "checked": 0,
        "completed": 0,
        "failed": 0,
        "still_pending": 0,
        "errors": 0,
    }

    cutoff = timezone.now() - timedelta(minutes=max_age_minutes)

    pending_qs = Transaction.objects.filter(
        status="pending",
        timestamp__lte=cutoff,
        transaction_type="purchase",
    )

    logger.info(f"Found {pending_qs.count()} pending transactions to recheck")

    for tx in pending_qs:
        stats["checked"] += 1
        logger.debug(f"Processing transaction {tx.reference}")

        try:
            # Check VTPass for transaction status
            vtpass_status = check_and_get_transaction_status(tx.reference)

            if vtpass_status is None:
                # Transaction doesn't exist on VTPass - mark as failed
                tx.status = "failed"
                tx.save()
                stats["failed"] += 1
                logger.info(f"Transaction {tx.reference} not found on VTPass. Marked as failed.")
            
            elif vtpass_status == "completed":
                tx.status = "completed"
                tx.save()
                stats["completed"] += 1
                logger.info(f"Transaction {tx.reference} completed on VTPass.")
            
            elif vtpass_status == "failed":
                tx.status = "failed"
                tx.save()
                stats["failed"] += 1
                logger.info(f"Transaction {tx.reference} failed on VTPass.")
            
            else:  # vtpass_status == "pending"
                stats["still_pending"] += 1
                logger.info(f"Transaction {tx.reference} still pending on VTPass.")

        except VTPassError as e:
            stats["errors"] += 1
            logger.error(f"Error checking transaction {tx.reference}: {e}")
        
        except Exception as e:
            stats["errors"] += 1
            logger.error(f"Unexpected error for transaction {tx.reference}: {e}")

    logger.info(f"Recheck complete. Stats: {stats}")
    return stats