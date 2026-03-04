import mysql.connector

# 数据库连接信息
config = {
    'user': 'root',
    'password': 'Tt153167..',
    'host': 'localhost',
    'port': 3306,
    'database': 'mysql'
}

# 连接到 MySQL 服务器
conn = mysql.connector.connect(**config)
cursor = conn.cursor()

# 删除并重新创建 CA 数据库
cursor.execute("DROP DATABASE IF EXISTS CA")
cursor.execute("CREATE DATABASE CA")
cursor.execute("USE CA")

# 关闭连接
cursor.close()
conn.close()

print("数据库重新初始化成功！")