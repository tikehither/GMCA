#!/usr/bin/env python3
"""
检查数据库中用户的密码哈希值
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseManager

def main():
    print("正在初始化数据库管理器...")
    db = DatabaseManager()
    
    # 查询数据库中的用户
    try:
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id, username, password_hash, role FROM users")
        users = cursor.fetchall()
        
        print("\n数据库中的用户:")
        for user in users:
            print(f"  ID: {user['id']}, 用户名: {user['username']}, 角色: {user['role']}")
            print(f"  密码哈希: {user['password_hash']}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"查询用户失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
