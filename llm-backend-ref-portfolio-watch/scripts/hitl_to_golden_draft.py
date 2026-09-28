#!/usr/bin/env python3
"""hitl_to_golden_draft.py - Lấy feedback tiêu cực từ HITL và tạo draft test case.

Đọc resources/data/hitl_feedback.json, lọc thumbs down, và xuất ra YAML.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

def generate_sample_feedback(path: Path) -> None:
    """Tạo mẫu hitl_feedback.sample.json nếu thiếu để phục vụ demo."""
    sample_data = [
        {
            "id": "sample_1",
            "timestamp": "2026-09-28T10:00:00Z",
            "session_id": "sess_001",
            "question": "FPT hôm nay thế nào?",
            "answer": "Không rõ.",
            "rating": 2,
            "is_positive": False,
            "reason": "Thiếu ý",
            "user_feedback": "Cần thêm thông tin giá hiện tại."
        },
        {
            "id": "sample_2",
            "timestamp": "2026-09-28T10:05:00Z",
            "session_id": "sess_002",
            "question": "Giá HPG?",
            "answer": "Giá HPG là 26000",
            "rating": 5,
            "is_positive": True,
            "reason": None,
            "user_feedback": "Tốt"
        }
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sample_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Created sample feedback file at {path}")

def process_feedback(input_path: Path, output_dir: Path, dry_run: bool = False) -> int:
    if not input_path.exists():
        sample_path = input_path.parent / "hitl_feedback.sample.json"
        if not sample_path.exists():
            generate_sample_feedback(sample_path)
        print(f"Input missing: {input_path}; using sample {sample_path}")
        input_path = sample_path

    try:
        content = input_path.read_text(encoding="utf-8")
        records = json.loads(content)
    except Exception as e:
        print(f"Error reading {input_path}: {e}")
        return 1
        
    if not isinstance(records, list):
        print(f"Error: Expected list in {input_path}")
        return 1

    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for record in records:
        is_positive = record.get("is_positive")
        rating = record.get("rating")
        
        # Filter thumbs-down: is_positive == False OR rating <= 2
        is_negative = False
        if is_positive is False:
            is_negative = True
        elif rating is not None and isinstance(rating, (int, float)) and rating <= 2:
            is_negative = True

        if is_negative:
            record_id = record.get("id", "unknown")
            short_id = record_id[:8] if len(record_id) > 8 else record_id
            draft_id = f"hitl_draft_{short_id}"
            
            question = record.get("question", "")
            reason = record.get("reason", "")
            feedback = record.get("user_feedback", "")
            expected = f"From HITL feedback: {reason}. {feedback}".strip()
            
            # YAML format
            draft_case = [{
                "id": draft_id,
                "question": question,
                "expected": expected,
                "slice": {
                    "type": "lookup",
                    "difficulty": "medium"
                },
                "must_include": [],
                "must_not_include": [],
                "metadata": {
                    "source": "hitl",
                    "original_feedback": feedback
                }
            }]
            
            yaml_content = yaml.dump(draft_case, allow_unicode=True, sort_keys=False)
            
            if dry_run:
                print(f"[DRY RUN] Would create {draft_id}.yaml:\n{yaml_content}\n")
            else:
                out_file = output_dir / f"{draft_id}.yaml"
                out_file.write_text(yaml_content, encoding="utf-8")
                print(f"Created {out_file}")
            count += 1

    print(f"Total draft cases generated: {count}")
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert negative HITL feedback into golden draft test cases.\n\n"
                    "If the input hitl_feedback.json is missing, the script will create a sample "
                    "at resources/data/hitl_feedback.sample.json.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    root = Path(__file__).resolve().parents[1]
    default_input = root / "resources" / "data" / "hitl_feedback.json"
    default_output = root / "resources" / "eval" / "drafts"
    
    parser.add_argument("--input", type=Path, default=default_input, help="Path to hitl_feedback.json")
    parser.add_argument("--output-dir", type=Path, default=default_output, help="Directory to save YAML drafts")
    parser.add_argument("--dry-run", action="store_true", help="Print YAML to stdout without writing files")
    
    args = parser.parse_args()
    return process_feedback(args.input, args.output_dir, args.dry_run)

if __name__ == "__main__":
    sys.exit(main())
