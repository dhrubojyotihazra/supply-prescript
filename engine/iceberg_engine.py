"""
SupplyPrescript - Week 4 Time Travel & Snapshot Engine
Apache Iceberg Snapshot Isolation & Data Rollback Engine

Provides:
1. Immutable snapshot history creation & auditing.
2. Time Travel Queries: Query exact state of data before anomaly occurred.
3. 1-Click Rollback: Instant data pointer restoration to pre-anomaly snapshot.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

class IcebergTableManager:
    def __init__(self):
        self.main_table = "warehouses_main_stream"
        self.dlq_table = "warehouses_dlq_stream"
        self.snapshots: List[Dict[str, Any]] = []
        self._seed_default_snapshots()

    def _seed_default_snapshots(self):
        now = datetime.utcnow()
        self.snapshots = [
            {
                "snapshot_id": "snap-1001",
                "table_name": self.main_table,
                "timestamp": (now - timedelta(hours=3)).isoformat(),
                "parent_snapshot_id": None,
                "record_count": 22000,
                "commit_summary": "Initial Table Initialization & Schema Seeding [Baseline]",
                "status": "VALID",
                "is_current": False
            },
            {
                "snapshot_id": "snap-1002",
                "table_name": self.main_table,
                "timestamp": (now - timedelta(hours=1, minutes=15)).isoformat(),
                "parent_snapshot_id": "snap-1001",
                "record_count": 22149,
                "commit_summary": "Pre-Anomaly Clean Data Ingestion [PRE-ANOMALY CHECKPOINT]",
                "status": "VALID",
                "is_current": True
            },
            {
                "snapshot_id": "snap-1003",
                "table_name": self.dlq_table,
                "timestamp": (now - timedelta(minutes=25)).isoformat(),
                "parent_snapshot_id": "snap-1002",
                "record_count": 145,
                "commit_summary": "Stream Anomaly Triggered (>2.0% Error Rate) -> Quarantined in DLQ Table",
                "status": "QUARANTINED_ANOMALY",
                "is_current": False
            }
        ]

    def get_snapshots(self, table_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns all registered Iceberg snapshots, optionally filtered by table."""
        if table_name:
            return [s for s in self.snapshots if s["table_name"] == table_name]
        return self.snapshots

    def get_snapshot_by_id(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        for s in self.snapshots:
            if s["snapshot_id"] == snapshot_id:
                return s
        return None

    def create_snapshot(
        self,
        table_name: str,
        commit_summary: str,
        record_count: int,
        status: str = "VALID"
    ) -> Dict[str, Any]:
        """Creates a new immutable Iceberg snapshot."""
        current_active = next((s for s in self.snapshots if s["table_name"] == table_name and s["is_current"]), None)
        parent_id = current_active["snapshot_id"] if current_active else None

        new_snap_id = f"snap-{1000 + len(self.snapshots) + 1}"

        # Reset is_current flag for previous current snapshot of this table
        if current_active:
            current_active["is_current"] = False

        new_snapshot = {
            "snapshot_id": new_snap_id,
            "table_name": table_name,
            "timestamp": datetime.utcnow().isoformat(),
            "parent_snapshot_id": parent_id,
            "record_count": record_count,
            "commit_summary": commit_summary,
            "status": status,
            "is_current": True
        }
        self.snapshots.append(new_snapshot)
        return new_snapshot

    def time_travel_query(self, snapshot_id: str) -> Dict[str, Any]:
        """
        Executes a Time Travel query using Iceberg snapshot isolation.
        Returns the exact state of data before/at the specified snapshot.
        """
        target_snapshot = self.get_snapshot_by_id(snapshot_id)
        if not target_snapshot:
            return {
                "status": "error",
                "message": f"Snapshot '{snapshot_id}' not found in Iceberg catalog."
            }

        # Simulated state data at the snapshot
        clean_sample_data = [
            {"warehouse_id": "WH_100001", "zone": "North", "status": "Normal", "capacity_size": "Large", "product_wg_ton": 14500},
            {"warehouse_id": "WH_100002", "zone": "South", "status": "Normal", "capacity_size": "Mid", "product_wg_ton": 8900},
            {"warehouse_id": "WH_100003", "zone": "East", "status": "Normal", "capacity_size": "Small", "product_wg_ton": 3200},
            {"warehouse_id": "WH_100004", "zone": "West", "status": "Normal", "capacity_size": "Large", "product_wg_ton": 18200},
            {"warehouse_id": "WH_100005", "zone": "Central", "status": "Normal", "capacity_size": "Mid", "product_wg_ton": 11000}
        ]

        return {
            "status": "success",
            "snapshot_id": target_snapshot["snapshot_id"],
            "table_name": target_snapshot["table_name"],
            "timestamp": target_snapshot["timestamp"],
            "commit_summary": target_snapshot["commit_summary"],
            "record_count": target_snapshot["record_count"],
            "is_pre_anomaly": target_snapshot["snapshot_id"] == "snap-1002",
            "schema_version": "v1.2-iceberg-parquet",
            "data_sample": clean_sample_data
        }

    def rollback_to_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        """
        Rolls back the main table's active pointer to a clean historical snapshot,
        eliminating corrupted stream effects without data loss in audit log.
        """
        target_snapshot = self.get_snapshot_by_id(snapshot_id)
        if not target_snapshot:
            return {
                "status": "error",
                "message": f"Cannot rollback: Snapshot '{snapshot_id}' does not exist."
            }

        # Mark all main table snapshots as non-current
        for s in self.snapshots:
            if s["table_name"] == self.main_table:
                s["is_current"] = False

        # Mark target as current or create rollback commit snapshot
        rollback_snap = self.create_snapshot(
            table_name=self.main_table,
            commit_summary=f"Data Rollback to Snapshot [{snapshot_id}] ({target_snapshot['commit_summary']})",
            record_count=target_snapshot["record_count"],
            status="ROLLED_BACK_RESTORED"
        )

        return {
            "status": "success",
            "restored_snapshot_id": snapshot_id,
            "new_rollback_snapshot_id": rollback_snap["snapshot_id"],
            "table_name": self.main_table,
            "restored_records": target_snapshot["record_count"],
            "timestamp": rollback_snap["timestamp"],
            "message": f"Successfully rolled back '{self.main_table}' to pre-anomaly state at snapshot [{snapshot_id}]."
        }

# Global singleton Iceberg manager instance
iceberg_manager = IcebergTableManager()
