#!/usr/bin/env python3
"""
更新 certificates 表的 status 字段，添加 'rejected' 选项
"""

import mysql.connector
from mysql.connector import Error

# 数据库连接配置
config = {
    'user': 'root',
    'password': 'Tt153167..',
    'host': 'localhost',
    'database': 'CA',
    'raise_on_warnings': True
}

def update_certificates_status_enum():
    """更新 certificates 表的 status 字段，添加 'rejected' 选项"""
    try:
        # 连接数据库
        conn = mysql.connector.connect(**config)
        if conn.is_connected():
            print("成功连接到数据库")
            
            # 创建游标
            cursor = conn.cursor()
            
            # 查看当前表结构
            print("\n当前 certificates 表结构:")
            cursor.execute("DESCRIBE certificates")
            for column in cursor.fetchall():
                if column[0] == 'status':
                    print(f"status 字段: {column}")
            
            # 更新 status 字段的 ENUM 定义
            print("\n更新 status 字段，添加 'rejected' 选项...")
            alter_sql = """
            ALTER TABLE certificates 
            MODIFY COLUMN status ENUM('pending', 'valid', 'revoked', 'rejected') DEFAULT 'pending'
            """
            
            cursor.execute(alter_sql)
            conn.commit()
            print("更新成功！")
            
            # 验证更新结果
            print("\n更新后的 certificates 表结构:")
            cursor.execute("DESCRIBE certificates")
            for column in cursor.fetchall():
                if column[0] == 'status':
                    print(f"status 字段: {column}")
            
            # 关闭游标和连接
            cursor.close()
            conn.close()
            print("\n数据库连接已关闭")
            
    except Error as e:
        print(f"数据库操作失败: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    update_certificates_status_enum()
