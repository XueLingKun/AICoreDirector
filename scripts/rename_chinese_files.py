#!/usr/bin/env python3
"""
Rename Chinese-named files and directories to English equivalents.
This script handles the migration of Chinese characters in file/directory names.

Usage: python -m scripts.rename_chinese_files
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

# Mapping of Chinese names to English equivalents
RENAME_RULES: Dict[str, str] = {
    # Directories
    "frontend - 副本": "frontend_backup",
    "config_prompts - 备份": "config_prompts_backup",
    
    # Files
    "README - 副本.md": "README_backup.md",
    "llm_models - 副本.yaml": "llm_models_copy.yaml", 
    "llm_models - 备份.yaml": "llm_models_backup.yaml",
    "llm_models - 待核对.yaml": "llm_models_pending.yaml",
    "llm_.yml": "llm_models.yml",
    "vite.config - 副本.js": "vite.config_backup.js",
    
    # Documents
    "总体架构图.svg": "architecture_overview.svg",
    "总体架构图1.png": "architecture_overview.png",
    "TPU流程图.png": "tpu_flowchart.png",
    "mermaid_1.png": "mermaid_architecture.png",
    "mermaid_2.png": "mermaid_flow.png",
    "mermaid_3.png": "mermaid_components.png",
    "mermaid_4.png": "mermaid_data_flow.png",
    "mermaid_5.png": "mermaid_api.png",
    "mermaid_6.png": "mermaid_deployment.png",
    "logo_main - 副本.svg": "logo_main_backup.svg",
    "test_svg.svg": "test_logo.svg",
    "MyVideo_2.gif": "demo_video.gif",
    "1752896896292.png": "screenshot_1.png",
    "E%5CML_NLP%5Ccode&course%5CAIHub%5Cdocs%5C总体架构图1.png": "architecture_diagram.png",
    
    # Business documents
    "AICoreDirector商业计划书.md": "AICoreDirector_business_plan.md",
    "AICoreDirector商业计划书v2.0.md": "AICoreDirector_business_plan_v2.md",
    "两级用户体系设计.md": "two_tier_user_system_design.md",
    "Design.md": "system_design.md",
}

def should_rename(path: Path) -> bool:
    """Check if a path should be renamed based on Chinese characters or spaces."""
    name = path.name
    # Check for Chinese characters
    if any('\u4e00' <= char <= '\u9fff' for char in name):
        return True
    # Check for spaces and special characters
    if ' ' in name or '&' in name or '%' in name:
        return True
    # Check for specific patterns
    if any(pattern in name for pattern in [' - ', '副本', '备份', '待核对']):
        return True
    return False

def find_rename_candidates(root: Path) -> List[Tuple[Path, str]]:
    """Find all files and directories that should be renamed."""
    candidates = []
    
    for item in root.rglob('*'):
        if should_rename(item):
            # Generate new name based on rules or default pattern
            new_name = RENAME_RULES.get(item.name, item.name)
            # Clean up the name
            new_name = new_name.replace(' ', '_').replace('&', 'and').replace('%', '')
            candidates.append((item, new_name))
    
    return candidates

def rename_items(candidates: List[Tuple[Path, str]], dry_run: bool = True) -> int:
    """Rename items. Returns count of renamed items."""
    renamed = 0
    
    for old_path, new_name in candidates:
        new_path = old_path.parent / new_name
        
        if dry_run:
            print(f"Would rename: {old_path} -> {new_path}")
        else:
            try:
                if old_path.exists():
                    if new_path.exists():
                        print(f"Skip (target exists): {old_path} -> {new_path}")
                        continue
                    
                    if old_path.is_file():
                        shutil.move(str(old_path), str(new_path))
                    else:
                        shutil.move(str(old_path), str(new_path))
                    
                    print(f"Renamed: {old_path} -> {new_path}")
                    renamed += 1
                else:
                    print(f"Skip (not found): {old_path}")
            except Exception as e:
                print(f"Error renaming {old_path}: {e}")
    
    return renamed

def main():
    """Main function to execute the renaming process."""
    root = Path(__file__).parent.parent
    print(f"Scanning for Chinese-named files in: {root}")
    
    # Find candidates
    candidates = find_rename_candidates(root)
    
    if not candidates:
        print("No files/directories found that need renaming.")
        return
    
    print(f"\nFound {len(candidates)} items to rename:")
    for old_path, new_name in candidates:
        print(f"  {old_path} -> {new_name}")
    
    # Show what would happen
    print("\n=== DRY RUN ===")
    rename_items(candidates, dry_run=True)
    
    # Ask for confirmation
    response = input("\nProceed with actual renaming? (y/N): ").strip().lower()
    if response == 'y':
        print("\n=== EXECUTING RENAMES ===")
        renamed = rename_items(candidates, dry_run=False)
        print(f"\nCompleted! Renamed {renamed} items.")
    else:
        print("Renaming cancelled.")

if __name__ == "__main__":
    main()
