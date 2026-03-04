#!/usr/bin/env python3
"""
更新数据库中用户的密码哈希值为正确的 SM3 哈希值
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseManager
from gmssl import sm3, func

def main():
    print("正在初始化数据库管理器...")
    db = DatabaseManager()
    
    # 获取 '123456' 的 SM3 哈希值
    password = '123456'
    data_bytes = password.encode('utf-8')
    data_list = func.bytes_to_list(data_bytes)
    password_hash = sm3.sm3_hash(data_list)
    print(f"'{password}' 的 SM3 哈希值: {password_hash}")
    
    # 更新数据库中的密码哈希值
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 更新 admin 用户的密码哈希
        cursor.execute("""
            UPDATE users 
            SET password_hash = %s 
            WHERE username = 'admin'
        """, (password_hash,))
        
        # 更新 user 用户的密码哈希
        cursor.execute("""
            UPDATE users 
            SET password_hash = %s 
            WHERE username = 'user'
        """, (password_hash,))
        
        conn.commit()
        print(f"成功更新 {cursor.rowcount} 行")
        
        cursor.close()
        conn.close()
        
        print("密码哈希值更新完成!")
        
    except Exception as e:
        print(f"更新密码哈希值失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
