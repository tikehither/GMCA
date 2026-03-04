#!/usr/bin/env python3
"""
数据库迁移脚本
将旧的数据库结构迁移到新的结构
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseManager
from gmssl import sm4, func
import hashlib

def calculate_fingerprint(public_key: str) -> str:
    """计算公钥指纹
    
    Args:
        public_key: 公钥字符串
        
    Returns:
        公钥指纹（SHA256哈希的前64个字符）
    """
    data_bytes = public_key.encode('utf-8')
    hash_result = hashlib.sha256(data_bytes).hexdigest()
    return hash_result[:64]

def encrypt_with_sm4(data: str, key: bytes) -> str:
    """使用SM4加密数据
    
    Args:
        data: 明文数据
        key: SM4密钥
        
    Returns:
        Base64编码的密文
    """
    try:
        # 将字符串转换为字节
        data_bytes = data.encode('utf-8')
        
        # 填充数据到16字节的倍数
        padding_len = 16 - (len(data_bytes) % 16)
        data_bytes += bytes([padding_len] * padding_len)
        
        # 分块加密
        encrypted = b''
        for i in range(0, len(data_bytes), 16):
            block = data_bytes[i:i+16]
            encrypted_block = sm4.sm4_encrypt(key, block)
            encrypted += encrypted_block
        
        # Base64编码
        import base64
        return base64.b64encode(encrypted).decode('utf-8')
    except Exception as e:
        print(f"SM4加密失败: {e}")
        return ""

def decrypt_with_sm4(encrypted_data: str, key: bytes) -> str:
    """使用SM4解密数据
    
    Args:
        encrypted_data: Base64编码的密文
        key: SM4密钥
        
    Returns:
        明文数据
    """
    try:
        import base64
        encrypted_bytes = base64.b64decode(encrypted_data)
        
        # 分块解密
        decrypted = b''
        for i in range(0, len(encrypted_bytes), 16):
            block = encrypted_bytes[i:i+16]
            decrypted_block = sm4.sm4_decrypt(key, block)
            decrypted += decrypted_block
        
        # 去除填充
        padding_len = decrypted[-1]
        decrypted = decrypted[:-padding_len]
        
        return decrypted.decode('utf-8')
    except Exception as e:
        print(f"SM4解密失败: {e}")
        return ""

def main():
    print("正在初始化数据库管理器...")
    db = DatabaseManager()
    
    # 获取SM4密钥
    sm4_key = db.crypto.sm4_key
    if not sm4_key:
        print("SM4密钥未初始化")
        return
    
    print("SM4密钥已获取")
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 检查key_pairs表是否存在
        cursor.execute("SHOW TABLES LIKE 'key_pairs'")
        if not cursor.fetchone():
            print("创建 key_pairs 表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS key_pairs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    public_key_encrypted TEXT NOT NULL,
                    public_key_fingerprint VARCHAR(64) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status ENUM('active', 'revoked') DEFAULT 'active',
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE KEY unique_fingerprint (public_key_fingerprint)
                )
            """)
            print("key_pairs 表创建成功")
        
        # 检查certificates表是否有public_key_fingerprint字段
        cursor.execute("DESCRIBE certificates")
        columns = cursor.fetchall()
        column_names = [col['Field'] for col in columns]
        
        if 'public_key' in column_names and 'public_key_fingerprint' not in column_names:
            print("修改 certificates 表结构...")
            
            # 添加public_key_fingerprint字段
            cursor.execute("""
                ALTER TABLE certificates 
                ADD COLUMN public_key_fingerprint VARCHAR(64) NOT NULL 
                AFTER subject_name
            """)
            
            # 更新现有的证书记录
            cursor.execute("""
                SELECT id, subject_name, public_key 
                FROM certificates 
                WHERE public_key IS NOT NULL
            """)
            certificates = cursor.fetchall()
            
            for cert in certificates:
                fingerprint = calculate_fingerprint(cert['public_key'])
                cursor.execute("""
                    UPDATE certificates 
                    SET public_key_fingerprint = %s 
                    WHERE id = %s
                """, (fingerprint, cert['id']))
            
            # 删除public_key字段
            cursor.execute("""
                ALTER TABLE certificates DROP COLUMN public_key
            """)
            
            conn.commit()
            print("certificates 表结构修改成功")
        
        # 检查template_permissions表是否有created_at字段
        if 'created_at' not in column_names:
            cursor.execute("""
                ALTER TABLE template_permissions 
                ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            """)
            conn.commit()
            print("template_permissions 表结构修改成功")
        
        cursor.close()
        conn.close()
        
        print("数据库迁移完成!")
        
    except Exception as e:
        print(f"数据库迁移失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
