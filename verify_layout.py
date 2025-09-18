#!/usr/bin/env python3
"""
验证文件布局
"""

import requests

BASE_URL = "http://localhost:8000/api"

def verify_layout():
    """验证文件布局"""
    print("验证文件布局...")
    
    try:
        # 获取文件列表
        response = requests.get(f"{BASE_URL}/prompts/list")
        files = response.json()["files"]
        
        print(f"\n当前文件列表 ({len(files)} 个文件):")
        print(f"{files}")
        
        # 分类文件
        normal_files = []
        backup_files = []
        
        for file in files:
            if any(keyword in file for keyword in ['_备份', '_删除备份', '_副本', '_恢复前备份']):
                backup_files.append(file)
            else:
                normal_files.append(file)
        
        print(f"\n普通文件 ({len(normal_files)} 个):")
        for file in normal_files:
            print(f"  - {file}")
        
        print(f"\n备份文件 ({len(backup_files)} 个):")
        for file in backup_files:
            print(f"  - {file}")
        
        print(f"\nAICoreDirector 项目布局验证完成！")
        print(f"✓ 普通文件区域将显示 {len(normal_files)} 个文件")
        print(f"✓ 备份文件区域将显示 {len(backup_files)} 个文件")
        
    except Exception as e:
        print(f"验证失败: {e}")

if __name__ == "__main__":
    verify_layout() 