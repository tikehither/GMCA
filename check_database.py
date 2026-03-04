import mysql.connector
import os
import sys

# 数据库连接信息
config = {
    'user': 'root',
    'password': 'Tt153167..',
    'host': 'localhost',
    'port': 3306,
    'database': 'CA'
}

try:
    # 连接到数据库
    conn = mysql.connector.connect(**config)
    print("成功连接到数据库 CA")
    
    # 创建游标
    cursor = conn.cursor()
    
    # 检查 certificates 表结构
    print("\n检查 certificates 表结构:")
    cursor.execute("DESCRIBE certificates")
    columns = cursor.fetchall()
    for column in columns:
        print(f"{column[0]} - {column[1]} - {column[2]}")
    
    # 检查是否存在 template_id 为 1 的模板
    print("\n检查证书模板:")
    cursor.execute("SELECT * FROM certificate_templates WHERE id = 1")
    template = cursor.fetchone()
    if template:
        print(f"模板 ID 1 存在: {template}")
    else:
        print("模板 ID 1 不存在")
    
    # 关闭游标和连接
    cursor.close()
    conn.close()
    print("\n数据库检查完成")
    
except Exception as e:
    print(f"数据库检查失败: {str(e)}")
    sys.exit(1)
