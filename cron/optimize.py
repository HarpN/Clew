import sys
import os
import asyncio
import logging
import datetime

# Ensure root workspace is on path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database import get_db_connection, dialect
from neuromorphic_subsystems import Hippocampus
from router import ModelRouter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clew.optimizer")

def prune_expired_rules():
    """
    [THREAT 1 PATCH] Sweeps and removes temporary, unlocked adaptation rules that have expired.
    Ensures cognitive parameters do not 'over-fit' to transient user behaviors.
    """
    sql = "DELETE FROM ai_adaptations WHERE expires_at < CURRENT_TIMESTAMP AND is_locked = 0;"
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(dialect.format_query(sql))
        logger.info("[HIPPOCAMPUS] Swept and purged expired unlocked temporary adaptations.")

async def main():
    logger.info("[HIPPOCAMPUS] Initiating nightly optimization routine...")
    
    # 1. Clean expired adaptations before starting the extraction sequence
    prune_expired_rules()
    
    # 2. Run memory consolidation loop
    router = ModelRouter()
    hippocampus = Hippocampus()
    
    consolidated = await hippocampus.consolidate_experience_loop(router)
    logger.info(f"[HIPPOCAMPUS] Nightly memory consolidation loop finished. Consolidated {consolidated} new system strategies.")

if __name__ == "__main__":
    asyncio.run(main())
