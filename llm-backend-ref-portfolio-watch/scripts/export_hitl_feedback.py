import argparse
import csv
import json
import os
import sys
from pathlib import Path

# Add src to PYTHONPATH if not already there
root_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root_dir / "src"))

from backend.database.connection import get_connection
from backend.database.repositories import HITLEvaluationRepository


def get_default_output_dir() -> Path:
    return root_dir / "resources" / "data"


def main():
    parser = argparse.ArgumentParser(description="Export HITL feedback from SQLite to JSON and CSV")
    parser.add_argument("--limit", type=int, default=1000, help="Maximum number of records to export")
    parser.add_argument("--session-id", type=str, help="Filter by session ID")
    parser.add_argument("--output-dir", type=str, help="Directory to save exports")
    args = parser.parse_args()

    out_dir = Path(args.output_dir) if args.output_dir else get_default_output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "hitl_feedback_export.json"
    csv_path = out_dir / "hitl_feedback_export.csv"

    conn = get_connection()
    try:
        repo = HITLEvaluationRepository(conn)
        if args.session_id:
            records = repo.list_by_session(args.session_id)
            # list_by_session doesn't have a limit, so we apply it here
            records = records[:args.limit]
        else:
            records = repo.list_all(limit=args.limit)

        export_data = []
        for r in records:
            export_data.append({
                "id": r.id,
                "timestamp": r.created_at,
                "session_id": r.session_id,
                "message_id": r.message_id,
                "question": r.question,
                "answer": r.answer,
                "rating": r.rating,
                "is_positive": r.is_positive,
                "reason": r.reason,
                "user_feedback": r.feedback,
            })

        # Write JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        # Write CSV
        if export_data:
            fieldnames = [
                "id", "timestamp", "session_id", "message_id", "question", 
                "answer", "rating", "is_positive", "reason", "user_feedback"
            ]
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in export_data:
                    writer.writerow(row)
        
        print(f"Exported {len(export_data)} records.")
        print(f"JSON: {json_path}")
        print(f"CSV:  {csv_path}")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
