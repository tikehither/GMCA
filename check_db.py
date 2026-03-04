import mysql.connector
from mysql.connector import Error

try:
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='Tt153167..',
        database='CA'
    )
    
    cursor = conn.cursor()
    cursor.execute('DESCRIBE certificates')
    columns = cursor.fetchall()
    
    print('certificates表结构:')
    for col in columns:
        print(f'  {col[0]} - {col[1]}')
    
    cursor.close()
    conn.close()
    
except Error as e:
    print(f'数据库连接错误: {e}')