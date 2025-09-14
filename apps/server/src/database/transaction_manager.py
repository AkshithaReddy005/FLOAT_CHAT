from typing import List, Dict, Generator, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import logging
from dataclasses import dataclass
from database.database import ArgoMeasurement, UploadedFile

@dataclass
class TransactionResult:
    successful_inserts: int
    failed_inserts: int
    duplicate_skips: int
    errors: List[str]
    chunk_results: List[Dict]

class ChunkedTransactionManager:
    """Production-grade chunked transaction manager for ARGO measurements"""

    def __init__(self, chunk_size: int = 100):
        self.chunk_size = chunk_size
        self.logger = logging.getLogger(__name__)

    def execute_chunked_insert(
        self,
        db: Session,
        measurements: List[Dict],
        file_record: Optional[Dict] = None
    ) -> TransactionResult:
        """Execute measurements insertion in isolated chunks to prevent cascade failures"""

        result = TransactionResult(0, 0, 0, [], [])

        if not measurements:
            self.logger.info("No measurements to process")
            return result

        # Split into chunks for isolated processing
        chunks = list(self._chunk_measurements(measurements, self.chunk_size))
        self.logger.info(f"Processing {len(measurements)} measurements in {len(chunks)} chunks of size {self.chunk_size}")

        # Process each chunk independently to isolate failures
        for i, chunk in enumerate(chunks):
            try:
                chunk_result = self._process_chunk(db, chunk, f"chunk_{i+1}")

                result.successful_inserts += chunk_result['successful_inserts']
                result.failed_inserts += chunk_result['failed_inserts']
                result.duplicate_skips += chunk_result['duplicate_skips']
                result.chunk_results.append(chunk_result)

                if chunk_result['errors']:
                    result.errors.extend(chunk_result['errors'])

                self.logger.info(f"Chunk {i+1}/{len(chunks)}: {chunk_result['successful_inserts']} inserted, "
                               f"{chunk_result['duplicate_skips']} duplicates, {chunk_result['failed_inserts']} failed")

            except Exception as e:
                self.logger.error(f"Critical error processing chunk {i+1}: {e}")
                result.errors.append(f"Chunk {i+1} critical failure: {e}")
                result.failed_inserts += len(chunk)

        # Insert file record only if we had successful inserts
        if file_record and result.successful_inserts > 0:
            try:
                self._insert_file_record(db, file_record, result.successful_inserts)
                self.logger.info(f"File record inserted with {result.successful_inserts} measurements")
            except Exception as e:
                self.logger.error(f"File record insertion failed: {e}")
                result.errors.append(f"File record failed: {e}")

        self.logger.info(f"Transaction complete: {result.successful_inserts} successful, "
                        f"{result.duplicate_skips} duplicates, {result.failed_inserts} failed")

        return result

    def _chunk_measurements(self, measurements: List[Dict], size: int) -> Generator[List[Dict], None, None]:
        """Split measurements into processing chunks"""
        for i in range(0, len(measurements), size):
            yield measurements[i:i + size]

    def _process_chunk(self, db: Session, chunk: List[Dict], chunk_id: str) -> Dict:
        """Process single chunk with isolated transaction and duplicate filtering"""
        chunk_result = {
            'chunk_id': chunk_id,
            'successful_inserts': 0,
            'failed_inserts': 0,
            'duplicate_skips': 0,
            'errors': []
        }

        # Pre-filter duplicates to avoid unnecessary processing
        filtered_chunk = self._filter_existing_measurements(db, chunk)
        chunk_result['duplicate_skips'] = len(chunk) - len(filtered_chunk)

        if not filtered_chunk:
            self.logger.debug(f"{chunk_id}: All measurements were duplicates")
            return chunk_result

        # Attempt batch insertion in isolated transaction
        try:
            # Create measurement objects
            db_measurements = []
            creation_errors = 0

            for measurement_data in filtered_chunk:
                try:
                    db_measurement = ArgoMeasurement(**measurement_data)
                    db_measurements.append(db_measurement)
                except Exception as e:
                    creation_errors += 1
                    chunk_result['errors'].append(f"Object creation failed: {e}")

            if creation_errors > 0:
                chunk_result['failed_inserts'] += creation_errors
                self.logger.warning(f"{chunk_id}: {creation_errors} measurements failed object creation")

            # Batch insert valid measurements
            if db_measurements:
                db.add_all(db_measurements)
                db.commit()
                chunk_result['successful_inserts'] = len(db_measurements)

        except IntegrityError as e:
            # Handle constraint violations - fallback to individual processing
            db.rollback()
            self.logger.warning(f"{chunk_id}: Batch insert failed with integrity error, processing individually")
            individual_results = self._handle_individual_inserts(db, filtered_chunk, chunk_id)
            chunk_result['successful_inserts'] = individual_results['successful_inserts']
            chunk_result['failed_inserts'] += individual_results['failed_inserts']
            chunk_result['duplicate_skips'] += individual_results['duplicate_skips']
            chunk_result['errors'].extend(individual_results['errors'])

        except Exception as e:
            # Unexpected error - rollback and mark all as failed
            db.rollback()
            chunk_result['failed_inserts'] = len(filtered_chunk)
            chunk_result['errors'].append(f"Unexpected error: {e}")
            self.logger.error(f"{chunk_id}: Unexpected transaction error: {e}")

        return chunk_result

    def _filter_existing_measurements(self, db: Session, measurements: List[Dict]) -> List[Dict]:
        """Pre-filter existing measurements using efficient batch query"""
        if not measurements:
            return []

        # Extract hashes for batch duplicate check
        hashes = [m.get('measurement_hash') for m in measurements if m.get('measurement_hash')]

        if not hashes:
            self.logger.warning("No measurement hashes found for duplicate checking")
            return measurements

        existing_hashes = set()
        batch_size = 500  # Reasonable batch size for hash queries

        # Query in batches to avoid SQL query length limits
        for i in range(0, len(hashes), batch_size):
            batch_hashes = hashes[i:i + batch_size]
            try:
                existing_batch = db.query(ArgoMeasurement.measurement_hash).filter(
                    ArgoMeasurement.measurement_hash.in_(batch_hashes)
                ).all()
                existing_hashes.update(h[0] for h in existing_batch)
            except Exception as e:
                self.logger.error(f"Duplicate check failed for batch {i//batch_size + 1}: {e}")
                # If duplicate check fails, process all measurements (less efficient but safe)
                return measurements

        # Filter out existing measurements
        filtered = [m for m in measurements if m.get('measurement_hash') not in existing_hashes]

        self.logger.debug(f"Filtered {len(measurements)} measurements to {len(filtered)} new ones "
                         f"({len(existing_hashes)} duplicates found)")

        return filtered

    def _handle_individual_inserts(self, db: Session, measurements: List[Dict], chunk_id: str) -> Dict:
        """Handle measurements individually when batch insert fails"""
        result = {
            'successful_inserts': 0,
            'failed_inserts': 0,
            'duplicate_skips': 0,
            'errors': []
        }

        for i, measurement_data in enumerate(measurements):
            try:
                db_measurement = ArgoMeasurement(**measurement_data)
                db.add(db_measurement)
                db.commit()
                result['successful_inserts'] += 1

            except IntegrityError:
                # Late-discovered duplicate or constraint violation
                db.rollback()
                result['duplicate_skips'] += 1

            except Exception as e:
                # Other errors during individual insert
                db.rollback()
                result['failed_inserts'] += 1
                result['errors'].append(f"{chunk_id}_item_{i}: {e}")

        self.logger.debug(f"{chunk_id} individual processing: {result['successful_inserts']} success, "
                         f"{result['duplicate_skips']} duplicates, {result['failed_inserts']} failed")

        return result

    def _insert_file_record(self, db: Session, file_data: Dict, actual_measurements: int):
        """Insert file record with actual successful measurement count"""
        try:
            # Update with actual measurement count
            file_record_data = file_data.copy()
            file_record_data['measurements_count'] = actual_measurements

            uploaded_file = UploadedFile(**file_record_data)
            db.add(uploaded_file)
            db.commit()

        except IntegrityError as e:
            # File already exists (duplicate file hash)
            db.rollback()
            self.logger.warning(f"File record already exists: {e}")
            raise

        except Exception as e:
            db.rollback()
            self.logger.error(f"File record insertion failed: {e}")
            raise