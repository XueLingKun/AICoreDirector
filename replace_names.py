#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量替换脚本 - 将项目中的AICoreDirector替换为AICoreDirector
"""

import os
import re
from pathlib import Path

def replace_in_file(file_path, old_name, new_name):
    """在单个文件中替换名称"""
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换内容
        new_content = content.replace(old_name, new_name)
        
        # 如果内容有变化，写回文件
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ 已更新内容: {file_path}")
            return True
        else:
            print(f"⏭️  内容无需更新: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ 处理文件失败 {file_path}: {e}")
        return False

def rename_file_if_needed(file_path, old_name, new_name):
    """重命名包含旧名称的文件"""
    try:
        old_filename = file_path.name
        if old_name in old_filename:
            new_filename = old_filename.replace(old_name, new_name)
            new_file_path = file_path.parent / new_filename
            
            # 重命名文件
            file_path.rename(new_file_path)
            print(f"🔄 已重命名: {old_filename} → {new_filename}")
            return new_file_path
        return file_path
    except Exception as e:
        print(f"❌ 重命名文件失败 {file_path}: {e}")
        return file_path

def should_process_file(file_path):
    """判断文件是否需要处理"""
    # 跳过二进制文件和不需要处理的文件
    skip_extensions = {'.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe', '.bin', '.obj', '.o'}
    skip_files = {'.git', '__pycache__', 'node_modules', '.venv', '.pytest_cache'}
    
    # 检查文件扩展名
    if file_path.suffix.lower() in skip_extensions:
        return False
    
    # 检查是否在需要跳过的目录中
    for part in file_path.parts:
        if part in skip_files:
            return False
    
    # 只处理文本文件
    text_extensions = {'.md', '.txt', '.py', '.js', '.vue', '.html', '.css', '.json', '.yml', '.yaml', '.ini', '.cfg', '.conf'}
    if file_path.suffix.lower() in text_extensions:
        return True
    
    # 对于没有扩展名的文件，尝试作为文本文件处理
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            f.read(1024)  # 尝试读取前1KB
        return True
    except:
        return False

def main():
    """主函数"""
    old_name = "AICoreDirector"
    new_name = "AICoreDirector"
    
    print(f"🔄 开始批量替换: {old_name} → {new_name}")
    print("=" * 50)
    
    # 获取项目根目录
    project_root = Path(".")
    total_files = 0
    updated_files = 0
    
    # 先处理文件重命名
    print("🔄 处理文件重命名...")
    renamed_files = 0
    for file_path in project_root.rglob("*"):
        if file_path.is_file():
            new_file_path = rename_file_if_needed(file_path, old_name, new_name)
            if new_file_path != file_path:
                renamed_files += 1
                file_path = new_file_path
    
    print(f"📁 重命名完成，共重命名 {renamed_files} 个文件")
    print("-" * 30)
    
    # 再处理文件内容替换
    print("🔄 处理文件内容替换...")
    for file_path in project_root.rglob("*"):
        if file_path.is_file() and should_process_file(file_path):
            total_files += 1
            if replace_in_file(file_path, old_name, new_name):
                updated_files += 1
    
    print("=" * 50)
    print(f"📊 替换完成!")
    print(f"   重命名文件数: {renamed_files}")
    print(f"   内容更新文件数: {updated_files}")
    print(f"   总处理文件数: {total_files}")
    
    if renamed_files > 0 or updated_files > 0:
        print(f"\n✅ 成功将 {old_name} 替换为 {new_name}")
        print("   建议: 运行 git status 查看变更，然后提交更改")
    else:
        print(f"\n⏭️  没有找到需要替换的内容")

if __name__ == "__main__":
    main()
