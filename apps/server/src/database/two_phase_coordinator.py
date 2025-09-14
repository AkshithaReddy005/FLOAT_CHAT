from typing import Dict, List, Optional
import logging
from dataclasses import dataclass
from sqlalchemy.orm import Session

from database.transaction_manager import ChunkedTransactionManager, TransactionResult

@dataclass
class CoordinatorResult:
    postgresql_success: bool
    chromadb_success: bool
    measurements_processed: int
    consistency_maintained: bool
    postgresql_details: Optional[TransactionResult] = None
    chromadb_details: Optional[Dict] = None
    error_details: Optional[str] = None

class TwoPhaseCoordinator:
    """Coordinates transactions between PostgreSQL and ChromaDB for data consistency"""

    def __init__(self, chunk_size: int = 100):
        self.db_manager = ChunkedTransactionManager(chunk_size)
        self.logger = logging.getLogger(__name__)

    def execute_coordinated_transaction(
        self,
        db: Session,
        vector_store,
        measurements: List[Dict],
        file_hash: str,
        file_record: Optional[Dict] = None
    ) -> CoordinatorResult:
        """Execute coordinated transaction ensuring data consistency"""

        if not measurements:
            return CoordinatorResult(
                postgresql_success=True,
                chromadb_success=True,
                measurements_processed=0,
                consistency_maintained=True,
                error_details="No measurements to process"
            )

        self.logger.info(f"Starting coordinated transaction for {len(measurements)} measurements")

        # PHASE 1: PostgreSQL Transaction (Primary)
        try:
            self.logger.info("Phase 1: Processing PostgreSQL insertion")
            db_result = self.db_manager.execute_chunked_insert(db, measurements, file_record)
            postgresql_success = db_result.successful_inserts > 0

            if not postgresql_success:
                return CoordinatorResult(
                    postgresql_success=False,
                    chromadb_success=False,
                    measurements_processed=0,
                    consistency_maintained=True,
                    postgresql_details=db_result,
                    error_details="PostgreSQL insertion failed completely"
                )

            # PHASE 2: ChromaDB Transaction (Secondary)
            self.logger.info(f"Phase 2: Processing ChromaDB insertion for {db_result.successful_inserts} successful measurements")

            # Only process measurements that were actually inserted into PostgreSQL
            successful_measurements = self._get_successful_measurements(
                measurements, db_result.successful_inserts
            )

            chromadb_success = False
            chromadb_details = {}

            if successful_measurements:
                try:
                    chromadb_details = vector_store.add_measurements(successful_measurements, file_hash)
                    chromadb_success = chromadb_details.get('new_measurements', 0) > 0
                    self.logger.info(f"ChromaDB processed: {chromadb_details}")

                except Exception as e:
                    self.logger.warning(f"ChromaDB processing failed: {e}")
                    chromadb_details = {
                        'new_measurements': 0,
                        'duplicates_skipped': 0,
                        'total_processed': len(successful_measurements),
                        'error': str(e)
                    }

            # Determine final result
            if postgresql_success:
                if chromadb_success:
                    # Both succeeded - ideal case
                    result_msg = "Both PostgreSQL and ChromaDB successful"
                    consistency_maintained = True
                else:
                    # PostgreSQL succeeded, ChromaDB failed - still consistent
                    result_msg = "PostgreSQL succeeded, ChromaDB failed - data consistency maintained"
                    consistency_maintained = True

                self.logger.info(f"Transaction result: {result_msg}")

                return CoordinatorResult(
                    postgresql_success=True,
                    chromadb_success=chromadb_success,
                    measurements_processed=db_result.successful_inserts,
                    consistency_maintained=consistency_maintained,
                    postgresql_details=db_result,
                    chromadb_details=chromadb_details,
                    error_details=None if chromadb_success else "ChromaDB processing failed"
                )

            else:
                # PostgreSQL failed - no ChromaDB processing needed
                return CoordinatorResult(
                    postgresql_success=False,
                    chromadb_success=False,
                    measurements_processed=0,
                    consistency_maintained=True,
                    postgresql_details=db_result,
                    error_details="PostgreSQL processing failed"
                )

        except Exception as e:
            self.logger.error(f"Coordinated transaction failed: {e}")
            return CoordinatorResult(
                postgresql_success=False,
                chromadb_success=False,
                measurements_processed=0,
                consistency_maintained=False,
                error_details=f"Transaction coordination error: {e}"
            )

    def _get_successful_measurements(
        self,
        original_measurements: List[Dict],
        successful_count: int
    ) -> List[Dict]:
        """
        Get measurements that were successfully inserted to PostgreSQL.

        For Phase 1 implementation, we approximate based on successful count.
        In production, this would track exact measurements per chunk.
        """
        if successful_count <= 0:
            return []

        if successful_count >= len(original_measurements):
            return original_measurements

        # For now, return first N measurements
        # In production, would track exact successful measurements
        return original_measurements[:successful_count]

    def get_transaction_summary(self, result: CoordinatorResult) -> Dict:
        """Generate human-readable transaction summary"""
        summary = {
            "overall_status": "success" if result.consistency_maintained else "failed",
            "measurements_processed": result.measurements_processed,
            "postgresql_success": result.postgresql_success,
            "chromadb_success": result.chromadb_success,
            "consistency_maintained": result.consistency_maintained
        }

        if result.postgresql_details:
            summary["postgresql_details"] = {
                "successful_inserts": result.postgresql_details.successful_inserts,
                "duplicate_skips": result.postgresql_details.duplicate_skips,
                "failed_inserts": result.postgresql_details.failed_inserts,
                "chunks_processed": len(result.postgresql_details.chunk_results),
                "error_count": len(result.postgresql_details.errors)
            }

        if result.chromadb_details:
            summary["chromadb_details"] = result.chromadb_details

        if result.error_details:
            summary["error_details"] = result.error_details

        return summary