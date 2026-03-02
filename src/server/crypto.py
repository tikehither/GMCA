"""
简化的国密算法实现 - 仅包含必要功能，用于测试
"""

import os
import base64
import json
import hashlib
import time
import secrets
from pathlib import Path
from datetime import datetime, timedelta


class CryptoUtilsSimple:
    """简化的国密算法工具类 - 仅用于测试"""
    
    def __init__(self):
        # 配置路径
        self.key_dir = Path(__file__).parent / "keys"
        self.key_dir.mkdir(exist_ok=True)
        
        # 密钥文件路径
        self.sm2_private_key = self.key_dir / "server.key"
        self.sm2_public_key = self.key_dir / "server.pem"
        self.sm4_key_file = self.key_dir / "sm4.key"
        self.root_cert_file = self.key_dir / "ca.crt"
        
        print(f"加密工具初始化，密钥目录: {self.key_dir}")
        
        # 确保目录存在
        self.key_dir.mkdir(exist_ok=True)
    
    def generate_sm2_key_pair(self):
        """生成 SM2 密钥对（模拟）"""
        print("生成 SM2 密钥对（模拟）")
        
        # 创建模拟密钥文件
        private_key = "-----BEGIN PRIVATE KEY-----\n模拟私钥内容\n-----END PRIVATE KEY-----"
        public_key = "-----BEGIN PUBLIC KEY-----\n模拟公钥内容\n-----END PUBLIC KEY-----"
        
        try:
            with open(self.sm2_private_key, 'w') as f:
                f.write(private_key)
            
            with open(self.sm2_public_key, 'w') as f:
                f.write(public_key)
            
            print(f"SM2 密钥对生成成功")
            print(f"私钥文件: {self.sm2_private_key}")
            print(f"公钥文件: {self.sm2_public_key}")
            return True
            
        except Exception as e:
            print(f"生成 SM2 密钥对失败: {e}")
            return False
    
    def sm3_hash(self, data: str) -> str:
        """SM3 哈希（使用 SHA256 模拟）"""
        try:
            # 使用 SHA256 模拟 SM3
            hash_result = hashlib.sha256(data.encode()).hexdigest()
            return hash_result
        except Exception as e:
            print(f"SM3 哈希失败: {e}")
            return "模拟哈希值"
    
    def sm2_encrypt(self, plaintext: str) -> str:
        """SM2 加密（模拟）"""
        try:
            # 模拟加密：Base64 编码
            encrypted = base64.b64encode(plaintext.encode()).decode()
            return encrypted
        except Exception as e:
            print(f"SM2 加密失败: {e}")
            return "模拟加密数据"
    
    def sm2_decrypt(self, ciphertext: str) -> str:
        """SM2 解密（模拟）"""
        try:
            # 模拟解密：Base64 解码
            decrypted = base64.b64decode(ciphertext).decode()
            return decrypted
        except Exception as e:
            print(f"SM2 解密失败: {e}")
            return "模拟解密数据"
    
    def sm2_sign(self, data: str) -> str:
        """SM2 签名（模拟）"""
        try:
            # 模拟签名：Base64 编码的固定值
            signature = base64.b64encode(f"signature_for_{data}".encode()).decode()
            return signature
        except Exception as e:
            print(f"SM2 签名失败: {e}")
            return "模拟签名"
    
    def sm4_encrypt_with_key(self, plaintext: str, key: str) -> str:
        """SM4 加密（模拟）"""
        try:
            # 模拟加密：Base64 编码
            encrypted = base64.b64encode(plaintext.encode()).decode()
            return encrypted
        except Exception as e:
            print(f"SM4 加密失败: {e}")
            return "模拟SM4加密数据"
    
    def sm4_decrypt_with_key(self, ciphertext: str, key: str) -> str:
        """SM4 解密（模拟）"""
        try:
            # 模拟解密：Base64 解码
            decrypted = base64.b64decode(ciphertext).decode()
            return decrypted
        except Exception as e:
            print(f"SM4 解密失败: {e}")
            return "模拟SM4解密数据"
    
    def generate_serial_number(self) -> str:
        """生成证书序列号"""
        timestamp = int(time.time() * 1000)
        random_part = secrets.token_hex(8)
        return f"{timestamp:016x}{random_part}"
    
    def generate_root_certificate(self) -> bool:
        """生成根证书"""
        try:
            # 创建简单的证书信息
            cert_info = {
                "version": "v3",
                "serial_number": "1",
                "subject": "CN=My Root CA",
                "issuer": "CN=My Root CA",
                "validity": {
                    "not_before": "20250101000000",
                    "not_after": "20350101000000"
                },
                "public_key": "模拟公钥",
                "signature": "模拟签名"
            }
            
            # 保存证书
            with open(self.root_cert_file, 'w') as f:
                json.dump(cert_info, f, indent=2)
            
            print(f"根证书生成成功: {self.root_cert_file}")
            return True
            
        except Exception as e:
            print(f"生成根证书失败: {e}")
            return False
    
    def is_root_certificate_exists(self) -> bool:
        """检查根证书是否存在"""
        return self.root_cert_file.exists()
    
    def get_public_key_pem(self) -> str:
        """获取 PEM 格式的公钥"""
        try:
            if self.sm2_public_key.exists():
                with open(self.sm2_public_key, 'r') as f:
                    return f.read()
            
            # 如果文件不存在，返回模拟公钥
            return "-----BEGIN PUBLIC KEY-----\n模拟公钥内容\n-----END PUBLIC KEY-----"
            
        except Exception as e:
            print(f"获取公钥失败: {e}")
            return "模拟公钥"


# 测试函数
def test_simple_crypto():
    """测试简化的国密算法功能"""
    print("=" * 60)
    print("测试简化的国密算法功能")
    print("=" * 60)
    
    crypto = CryptoUtilsSimple()
    
    # 测试所有必要方法
    test_data = "测试数据"
    
    print("\n1. 测试 generate_sm2_key_pair():")
    result = crypto.generate_sm2_key_pair()
    print(f"   结果: {result}")
    
    print("\n2. 测试 sm3_hash():")
    hash_result = crypto.sm3_hash(test_data)
    print(f"   哈希值: {hash_result[:20]}...")
    
    print("\n3. 测试 sm2_encrypt() 和 sm2_decrypt():")
    encrypted = crypto.sm2_encrypt(test_data)
    print(f"   加密: {encrypted[:20]}...")
    decrypted = crypto.sm2_decrypt(encrypted)
    print(f"   解密: {decrypted}")
    print(f"   匹配: {decrypted == test_data}")
    
    print("\n4. 测试 sm2_sign():")
    signature = crypto.sm2_sign(test_data)
    print(f"   签名: {signature[:20]}...")
    
    print("\n5. 测试 generate_serial_number():")
    serial = crypto.generate_serial_number()
    print(f"   序列号: {serial}")
    
    print("\n6. 测试 generate_root_certificate():")
    if not crypto.is_root_certificate_exists():
        result = crypto.generate_root_certificate()
        print(f"   生成结果: {result}")
    else:
        print("   根证书已存在")
    
    print("\n7. 测试 get_public_key_pem():")
    pubkey = crypto.get_public_key_pem()
    print(f"   公钥: {pubkey[:50]}...")
    
    print("\n" + "=" * 60)
    print("简化测试完成 - 所有方法可用")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    test_simple_crypto()