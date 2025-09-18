"""
Rename Chinese prompt backup suffixes to English in config_prompts.

Chinese suffixes -> English suffixes
- _备份 -> _backup
- _删除备份 -> _delete_backup
- _恢复前备份 -> _pre_restore_backup
- _副本 -> _copy

This script is idempotent. Run from repository root:
  python -m scripts.migrate_prompt_backups
"""
from __future__ import annotations
import os
from typing import List, Tuple

ROOT = os.path.dirname(os.path.dirname(__file__))
PROMPT_DIR = os.path.join(ROOT, "config_prompts")

RULES: List[Tuple[str, str]] = [
    ("_删除备份", "_delete_backup"),
    ("_恢复前备份", "_pre_restore_backup"),
    ("_备份", "_backup"),
    ("_副本", "_copy"),
]

def generate_new_name(name: str) -> str:
    new_name = name
    for old, new in RULES:
        if old in new_name:
            new_name = new_name.replace(old, new)
    return new_name

def migrate() -> int:
    if not os.path.isdir(PROMPT_DIR):
        print(f"Prompt dir not found: {PROMPT_DIR}")
        return 0
    renamed = 0
    for entry in os.listdir(PROMPT_DIR):
        src = os.path.join(PROMPT_DIR, entry)
        if not os.path.isfile(src):
            continue
        dst_name = generate_new_name(entry)
        if dst_name != entry:
            dst = os.path.join(PROMPT_DIR, dst_name)
            if os.path.exists(dst):
                print(f"Skip rename (target exists): {entry} -> {dst_name}")
                continue
            os.rename(src, dst)
            print(f"Renamed: {entry} -> {dst_name}")
            renamed += 1
    print(f"Done. Total renamed: {renamed}")
    return renamed

if __name__ == "__main__":
    migrate()


