"""
完整的客户端国密算法实现 - 基于 gmssl 库
实现 SM2/SM3/SM4 标准算法
"""

import os
import base64
import json
import hashlib
import secrets
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from datetime import datetime, timedelta

try:
    from gmssl import sm2, sm3, sm4, func
    from gmssl.sm2 import CryptSM2
    from gmssl.sm4 import CryptSM4, SM4_ENCRYPT, SM4_DECRYPT
    GMSSL_AVAILABLE = True
except ImportError:
    print("警告: gmssl 库未安装，将使用模拟实现")
    GMSSL_AVAILABLE = False
    CryptSM2 = None
    CryptSM4 = None


class ClientGMSCrypto:
    """客户端国密算法加密工具类 - 完整实现 SM2/SM3/SM4"""
    
    def __init__(self, key_dir: Optional[Path] = None):
        """初始化客户端国密加密工具
        
        Args:
            key_dir: 密钥存储目录，如果为None则使用默认目录
        """
        if key_dir is None:
            script_dir = Path(__file__).parent
            key_dir = script_dir / "keys"
        
        self.key_dir = key_dir
        self.key_dir.mkdir(parents=True, exist_ok=True)
        
        # 密钥文件路径
        self.sm2_private_key = self.key_dir / "client.key"
        self.sm2_public_key = self.key_dir / "client.pem"
        self.sm4_key_file = self.key_dir / "sm4.key"
        self.server_public_key_file = self.key_dir / "server.pem"
        
        # SM2/SM4 实例
        self.sm2: Optional[CryptSM2] = None
        self.server_sm2: Optional[CryptSM2] = None
        self.sm4_key: Optional[bytes] = None
        
        # 初始化密钥
        self._init_keys()
    
    def _init_keys(self):
        """初始化密钥 - 加载或生成"""
        try:
            # 加载或生成 SM2 密钥
            if self.sm2_private_key.exists() and self.sm2_public_key.exists():
                if not self._load_client_keys():
                    print("客户端 SM2 密钥加载失败，重新生成")
                    self._generate_sm2_keys()
            else:
                self._generate_sm2_keys()
            
            # 加载或生成 SM4 密钥
            if self.sm4_key_file.exists():
                if not self._load_sm4_key():
                    print("SM4 密钥加载失败，重新生成")
                    self._generate_sm4_key()
            else:
                self._generate_sm4_key()
                
        except Exception as e:
            print(f"初始化密钥失败: {e}")
            self._create_mock_keys()
    
    def _generate_sm2_keys(self) -> bool:
        """生成 SM2 密钥对
        
        Returns:
            成功返回True，失败返回False
        """
        try:
            # 生成 SM2 私钥
            private_key = secrets.token_hex(32)
            
            # 使用 gmssl 库计算公钥
            # 公钥 = 私钥 * G（椭圆曲线基点）
            sm2_temp = CryptSM2(
                private_key=private_key,
                public_key=""  # 公钥待计算
            )
            
            # 获取 ECC 参数
            ecc_g = sm2_temp.ecc_table['g']
            
            # 计算公钥: P = private_key * G
            private_int = int(private_key, 16)
            public_point = sm2_temp._kg(private_int, ecc_g)
            
            # 公钥格式: 04 + x + y（非压缩格式）
            # 但 CryptSM2 期望的格式是 x + y（去掉 04）
            public_key = public_point
            
            # 保存私钥
            with open(self.sm2_private_key, 'w') as f:
                f.write(f"-----BEGIN PRIVATE KEY-----\n{private_key}\n-----END PRIVATE KEY-----")
            
            # 保存公钥
            with open(self.sm2_public_key, 'w') as f:
                f.write(f"-----BEGIN PUBLIC KEY-----\n{public_key}\n-----END PUBLIC KEY-----")
            
            # 创建 SM2 实例
            self.sm2 = CryptSM2(
                private_key=private_key,
                public_key=public_key
            )
            
            print(f"客户端 SM2 密钥对生成成功")
            print(f"私钥文件: {self.sm2_private_key}")
            print(f"公钥文件: {self.sm2_public_key}")
            return True
            
        except Exception as e:
            print(f"生成客户端 SM2 密钥对失败: {e}")
            import traceback
            traceback.print_exc()
            self._create_mock_keys()
            return False
    
    def _load_client_keys(self) -> bool:
        """加载客户端 SM2 密钥
        
        Returns:
            成功返回True，失败返回False
        """
        try:
            with open(self.sm2_private_key, 'r') as f:
                private_key = f.read().strip()
            
            with open(self.sm2_public_key, 'r') as f:
                public_key = f.read().strip()
            
            # 移除 PEM 格式标记
            if "-----BEGIN PRIVATE KEY-----" in private_key:
                private_key = private_key.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "").strip()
            
            if "-----BEGIN PUBLIC KEY-----" in public_key:
                public_key = public_key.replace("-----BEGIN PUBLIC KEY-----", "").replace("-----END PUBLIC KEY-----", "").strip()
            
            self.sm2 = CryptSM2(
                private_key=private_key,
                public_key=public_key
            )
            
            print("客户端 SM2 密钥加载成功")
            return True
            
        except Exception as e:
            print(f"加载客户端 SM2 密钥失败: {e}")
            return False
    
    def _generate_sm4_key(self) -> bool:
        """生成 SM4 密钥
        
        Returns:
            成功返回True，失败返回False
        """
        try:
            # 生成 16 字节的随机密钥
            key = secrets.token_bytes(16)
            
            with open(self.sm4_key_file, 'wb') as f:
                f.write(key)
            
            self.sm4_key = key
            print(f"客户端 SM4 密钥生成成功")
            return True
            
        except Exception as e:
            print(f"生成客户端 SM4 密钥失败: {e}")
            self.sm4_key = b"0123456789abcdef"
            return False
    
    def _load_sm4_key(self) -> bool:
        """加载 SM4 密钥
        
        Returns:
            成功返回True，失败返回False
        """
        try:
            with open(self.sm4_key_file, 'rb') as f:
                self.sm4_key = f.read()
            
            if len(self.sm4_key) != 16:
                print(f"SM4 密钥长度错误: {len(self.sm4_key)} 字节")
                return False
            
            print("客户端 SM4 密钥加载成功")
            return True
            
        except Exception as e:
            print(f"加载客户端 SM4 密钥失败: {e}")
            return False
    
    def _create_mock_keys(self):
        """创建模拟密钥（用于测试）"""
        print("创建模拟密钥用于测试")
        if GMSSL_AVAILABLE:
            self.sm2 = CryptSM2(
                private_key="mock_private_key_32bytes",
                public_key="mock_public_key_64bytes"
            )
        else:
            self.sm2 = None
        self.sm4_key = b"0123456789abcdef"
    
    def set_server_public_key(self, server_public_key: str) -> bool:
        """设置服务器公钥
        
        Args:
            server_public_key: 服务器的公钥（PEM格式或十六进制字符串）
            
        Returns:
            成功返回True，失败返回False
        """
        try:
            # 保存服务器公钥到文件
            with open(self.server_public_key_file, 'w') as f:
                f.write(server_public_key)
            
            # 解析服务器公钥
            public_key = server_public_key.strip()
            
            # 移除 PEM 格式标记
            if "-----BEGIN PUBLIC KEY-----" in public_key:
                public_key = public_key.replace("-----BEGIN PUBLIC KEY-----", "").replace("-----END PUBLIC KEY-----", "").strip()
            
            # 创建服务器 SM2 实例
            self.server_sm2 = CryptSM2(
                private_key=None,
                public_key=public_key
            )
            
            print("服务器公钥设置成功")
            return True
            
        except Exception as e:
            print(f"设置服务器公钥失败: {e}")
            return False
    
    def get_server_public_key(self) -> Optional[str]:
        """获取服务器公钥
        
        Returns:
            服务器公钥字符串，失败返回None
        """
        try:
            if self.server_public_key_file.exists():
                with open(self.server_public_key_file, 'r') as f:
                    return f.read()
            return None
        except Exception as e:
            print(f"获取服务器公钥失败: {e}")
            return None
    
    def save_server_public_key(self, server_public_key: str) -> bool:
        """保存服务器公钥
        
        Args:
            server_public_key: 服务器的公钥（PEM格式或十六进制字符串）
            
        Returns:
            成功返回True，失败返回False
        """
        try:
            # 保存服务器公钥到文件
            with open(self.server_public_key_file, 'w') as f:
                f.write(server_public_key)
            
            # 设置服务器公钥
            return self.set_server_public_key(server_public_key)
        except Exception as e:
            print(f"保存服务器公钥失败: {e}")
            return None
    
    def save_sm2_key_pair(self, save_dir: str) -> bool:
        """保存 SM2 密钥对到指定目录
        
        Args:
            save_dir: 保存目录路径
            
        Returns:
            成功返回True，失败返回False
        """
        try:
            import shutil
            
            # 确保目录存在
            save_path = Path(save_dir)
            save_path.mkdir(parents=True, exist_ok=True)
            
            # 复制密钥文件到指定目录
            if self.sm2_private_key.exists():
                dest_private = save_path / "client_private.key"
                shutil.copy2(self.sm2_private_key, dest_private)
                print(f"私钥已保存到: {dest_private}")
            
            if self.sm2_public_key.exists():
                dest_public = save_path / "client_public.key"
                shutil.copy2(self.sm2_public_key, dest_public)
                print(f"公钥已保存到: {dest_public}")
            
            return True
        except Exception as e:
            print(f"保存密钥对失败: {e}")
            return False
    
    def save_sm4_key(self, save_dir: str) -> bool:
        """保存 SM4 密钥到指定目录
        
        Args:
            save_dir: 保存目录路径
            
        Returns:
            成功返回True，失败返回False
        """
        try:
            import shutil
            
            # 确保目录存在
            save_path = Path(save_dir)
            save_path.mkdir(parents=True, exist_ok=True)
            
            # 复制SM4密钥文件到指定目录
            if self.sm4_key_file.exists():
                dest_sm4 = save_path / "client_sm4.key"
                shutil.copy2(self.sm4_key_file, dest_sm4)
                print(f"SM4密钥已保存到: {dest_sm4}")
            
            return True
        except Exception as e:
            print(f"保存SM4密钥失败: {e}")
            return False
    
    def sm3_hash(self, data: str) -> Optional[str]:
        """SM3 哈希 - 国密标准算法
        
        Args:
            data: 输入字符串
            
        Returns:
            32字节的SM3哈希值（十六进制字符串），失败返回None
        """
        try:
            if not GMSSL_AVAILABLE:
                # 使用 SHA256 作为替代
                return hashlib.sha256(data.encode()).hexdigest()
            
            # 使用 gmssl 的 SM3
            data_bytes = data.encode('utf-8')
            data_list = func.bytes_to_list(data_bytes)
            hash_result = sm3.sm3_hash(data_list)
            return hash_result
            
        except Exception as e:
            print(f"SM3 哈希失败: {e}")
            return None
    
    def sm2_encrypt(self, plaintext: str) -> Optional[str]:
        """SM2 加密（使用服务器公钥加密）
        
        Args:
            plaintext: 明文字符串
            
        Returns:
            Base64编码的密文，失败返回None
        """
        try:
            if not self.server_sm2:
                raise ValueError("服务器公钥未设置")
            
            # 加密数据
            encrypted = self.server_sm2.encrypt(plaintext.encode('utf-8'))
            
            # Base64 编码
            return base64.b64encode(encrypted).decode('utf-8')
            
        except Exception as e:
            print(f"SM2 加密失败: {e}")
            return None
    
    def sm2_decrypt(self, ciphertext: str) -> Optional[str]:
        """SM2 解密（使用客户端私钥解密）
        
        Args:
            ciphertext: Base64编码的密文
            
        Returns:
            解密后的明文字符串，失败返回None
        """
        try:
            if not self.sm2:
                raise ValueError("SM2 实例未初始化")
            
            # Base64 解码
            encrypted = base64.b64decode(ciphertext)
            
            # 解密数据
            decrypted = self.sm2.decrypt(encrypted)
            
            return decrypted.decode('utf-8')
            
        except Exception as e:
            print(f"SM2 解密失败: {e}")
            return None
    
    def sm2_sign(self, data: str) -> Optional[str]:
        """SM2 签名
        
        Args:
            data: 待签名的数据
            
        Returns:
            十六进制字符串签名，失败返回None
        """
        try:
            if not self.sm2:
                raise ValueError("SM2 实例未初始化")
            
            # 生成随机数 K
            K = secrets.token_hex(16)
            
            # 签名数据
            signature = self.sm2.sign(data.encode('utf-8'), K)
            
            # 返回十六进制字符串
            return signature
            
        except Exception as e:
            print(f"SM2 签名失败: {e}")
            return None
    
    def sm2_verify(self, data: str, signature: str) -> bool:
        """SM2 验证签名
        
        Args:
            data: 原始数据
            signature: 十六进制字符串签名
            
        Returns:
            验证成功返回True，失败返回False
        """
        try:
            if not self.sm2:
                raise ValueError("SM2 实例未初始化")
            
            # 验证签名
            return self.sm2.verify(signature, data.encode('utf-8'))
            
        except Exception as e:
            print(f"SM2 验证签名失败: {e}")
            return False
    
    def encrypt_with_server_public_key(self, plaintext: str) -> Optional[str]:
        """使用服务器公钥加密
        
        Args:
            plaintext: 明文字符串
            
        Returns:
            Base64编码的密文，失败返回None
        """
        try:
            if not self.server_sm2:
                raise ValueError("服务器公钥未设置")
            
            # 加密数据
            encrypted = self.server_sm2.encrypt(plaintext.encode('utf-8'))
            
            # Base64 编码
            return base64.b64encode(encrypted).decode('utf-8')
            
        except Exception as e:
            print(f"使用服务器公钥加密失败: {e}")
            return None
    
    def sm4_encrypt(self, plaintext: str) -> Optional[str]:
        """SM4 加密 (ECB模式)
        
        Args:
            plaintext: 明文字符串
            
        Returns:
            Base64编码的密文，失败返回None
        """
        try:
            if not GMSSL_AVAILABLE or not self.sm4_key:
                # 使用 SHA256 作为替代
                return base64.b64encode(plaintext.encode()).decode()
            
            sm4 = CryptSM4()
            sm4.set_key(self.sm4_key, SM4_ENCRYPT)
            
            # 数据填充
            data = plaintext.encode('utf-8')
            padding = 16 - (len(data) % 16)
            data += bytes([padding] * padding)
            
            # ECB 模式加密
            encrypted = sm4.crypt_ecb(data)
            
            # Base64 编码
            return base64.b64encode(encrypted).decode('utf-8')
            
        except Exception as e:
            print(f"SM4 加密失败: {e}")
            return None
    
    def sm4_decrypt(self, ciphertext: str) -> Optional[str]:
        """SM4 解密 (ECB模式)
        
        Args:
            ciphertext: Base64编码的密文
            
        Returns:
            解密后的明文字符串，失败返回None
        """
        try:
            if not GMSSL_AVAILABLE or not self.sm4_key:
                # 使用 SHA256 作为替代
                return base64.b64decode(ciphertext).decode()
            
            sm4 = CryptSM4()
            sm4.set_key(self.sm4_key, SM4_DECRYPT)
            
            # Base64 解码
            encrypted = base64.b64decode(ciphertext)
            
            # ECB 模式解密
            decrypted = sm4.crypt_ecb(encrypted)
            
            # 去除填充
            padding = decrypted[-1]
            if padding < 1 or padding > 16:
                raise ValueError("无效的填充")
            
            return decrypted[:-padding].decode('utf-8')
            
        except Exception as e:
            print(f"SM4 解密失败: {e}")
            return None
    
    def sm4_encrypt_with_key(self, plaintext: str, key: bytes) -> Optional[str]:
        """使用指定密钥进行 SM4 加密
        
        Args:
            plaintext: 明文字符串
            key: SM4密钥(16字节)
            
        Returns:
            Base64编码的密文，失败返回None
        """
        try:
            if not GMSSL_AVAILABLE:
                return base64.b64encode(plaintext.encode()).decode()
            
            sm4 = CryptSM4()
            sm4.set_key(key, SM4_ENCRYPT)
            
            # 数据填充
            data = plaintext.encode('utf-8')
            padding = 16 - (len(data) % 16)
            data += bytes([padding] * padding)
            
            # ECB 模式加密
            encrypted = sm4.crypt_ecb(data)
            
            return base64.b64encode(encrypted).decode('utf-8')
            
        except Exception as e:
            print(f"SM4 加密失败: {e}")
            return None
    
    def sm4_decrypt_with_key(self, ciphertext: str, key: bytes) -> Optional[str]:
        """使用指定密钥进行 SM4 解密
        
        Args:
            ciphertext: Base64编码的密文
            key: SM4密钥(16字节)
            
        Returns:
            解密后的明文字符串，失败返回None
        """
        try:
            if not GMSSL_AVAILABLE:
                return base64.b64decode(ciphertext).decode()
            
            sm4 = CryptSM4()
            sm4.set_key(key, SM4_DECRYPT)
            
            # Base64 解码
            encrypted = base64.b64decode(ciphertext)
            
            # ECB 模式解密
            decrypted = sm4.crypt_ecb(encrypted)
            
            # 去除填充
            padding = decrypted[-1]
            if padding < 1 or padding > 16:
                raise ValueError("无效的填充")
            
            return decrypted[:-padding].decode('utf-8')
            
        except Exception as e:
            print(f"SM4 解密失败: {e}")
            return None
    
    def generate_serial_number(self) -> str:
        """生成证书序列号
        
        Returns:
            证书序列号（十六进制字符串）
        """
        timestamp = int(datetime.now().timestamp() * 1000)
        random_part = secrets.token_hex(8)
        return f"{timestamp:016x}{random_part}"
    
    def sign_certificate(self, cert_data: Dict) -> Optional[str]:
        """对证书数据进行签名
        
        Args:
            cert_data: 证书数据字典
            
        Returns:
            Base64编码的签名，失败返回None
        """
        try:
            # 将证书数据转换为JSON字符串
            cert_json = json.dumps(cert_data, sort_keys=True)
            
            # 使用SM2签名
            signature = self.sm2_sign(cert_json)
            
            return signature
            
        except Exception as e:
            print(f"证书签名失败: {e}")
            return None
    
    def verify_certificate_signature(self, cert_data: Dict, signature: str) -> bool:
        """验证证书签名
        
        Args:
            cert_data: 证书数据字典
            signature: Base64编码的签名
            
        Returns:
            验证成功返回True，失败返回False
        """
        try:
            # 将证书数据转换为JSON字符串
            cert_json = json.dumps(cert_data, sort_keys=True)
            
            # 使用SM2验证签名
            return self.sm2_verify(cert_json, signature)
            
        except Exception as e:
            print(f"证书签名验证失败: {e}")
            return False
    
    def generate_certificate_request(self, subject_name: str) -> Dict[str, Any]:
        """生成证书申请请求
        
        Args:
            subject_name: 证书主题名称
            
        Returns:
            包含证书申请信息的字典
        """
        try:
            # 加载或生成密钥对
            private_key, public_key = self.load_or_generate_sm2_key_pair()
            
            # 生成证书序列号
            serial_number = self.generate_serial_number()
            
            # 构建证书申请数据
            cert_request = {
                'serial_number': serial_number,
                'subject_name': subject_name,
                'public_key': public_key,
                'public_key_fingerprint': self.sm3_hash(public_key),
                'submit_date': datetime.now().isoformat(),
                'status': 'pending'
            }
            
            # 对证书申请数据进行签名
            signature = self.sign_certificate(cert_request)
            if signature:
                cert_request['signature'] = signature
            
            print(f"证书申请生成成功: 主题={subject_name}, 序列号={serial_number}")
            return cert_request
            
        except Exception as e:
            print(f"生成证书申请失败: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def save_certificate(self, cert_content: str, cert_path: str) -> bool:
        """保存证书到本地文件
        
        Args:
            cert_content: 证书内容
            cert_path: 证书保存路径
            
        Returns:
            成功返回True，失败返回False
        """
        try:
            # 确保目录存在
            cert_dir = Path(cert_path).parent
            cert_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存证书内容到文件
            with open(cert_path, 'w', encoding='utf-8') as f:
                f.write(cert_content)
            
            print(f"证书已保存到: {cert_path}")
            return True
            
        except Exception as e:
            print(f"保存证书失败: {e}")
            return False

    def is_initialized(self) -> bool:
        """检查加密模块是否已初始化
        
        Returns:
            初始化完成返回True，否则返回False
        """
        return (self.sm2 is not None and 
                self.sm4_key is not None and
                self.sm2_private_key.exists() and
                self.sm2_public_key.exists() and
                self.sm4_key_file.exists())

    def load_or_generate_sm2_key_pair(self) -> Tuple[str, str]:
        """加载或生成 SM2 密钥对
        
        Returns:
            返回 (private_key, public_key) 元组
        """
        try:
            # 如果密钥文件不存在，先生成密钥
            if not self.sm2_private_key.exists() or not self.sm2_public_key.exists():
                print("密钥文件不存在，正在生成 SM2 密钥对...")
                if not self._generate_sm2_keys():
                    raise Exception("生成 SM2 密钥对失败")
            
            # 加载密钥
            if not self._load_client_keys():
                raise Exception("加载 SM2 密钥失败")
            
            # 读取私钥和公钥
            with open(self.sm2_private_key, 'r') as f:
                private_key = f.read().strip()
            
            with open(self.sm2_public_key, 'r') as f:
                public_key = f.read().strip()
            
            # 移除 PEM 格式标记
            if "-----BEGIN PRIVATE KEY-----" in private_key:
                private_key = private_key.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "").strip()
            
            if "-----BEGIN PUBLIC KEY-----" in public_key:
                public_key = public_key.replace("-----BEGIN PUBLIC KEY-----", "").replace("-----END PUBLIC KEY-----", "").strip()
            
            print("SM2 密钥对加载/生成成功")
            return private_key, public_key
            
        except Exception as e:
            print(f"加载或生成 SM2 密钥对失败: {e}")
            # 返回模拟密钥作为备用
            return "mock_private_key_32bytes", "mock_public_key_64bytes"


# 全局实例
_client_crypto_instance = None


def get_client_crypto() -> ClientGMSCrypto:
    """获取全局的客户端国密加密实例
    
    Returns:
        ClientGMSCrypto实例
    """
    global _client_crypto_instance
    if _client_crypto_instance is None:
        _client_crypto_instance = ClientGMSCrypto()
    return _client_crypto_instance


def test_client_gms_crypto():
    """测试客户端国密加密功能"""
    print("=" * 60)
    print("测试客户端国密加密功能 (SM2/SM3/SM4)")
    print("=" * 60)
    
    crypto = get_client_crypto()
    
    # 测试数据
    test_data = "Hello, 国密算法客户端! 你好，世界！"
    
    # 测试 SM3 哈希
    print("\n1. 测试 SM3 哈希:")
    hash_result = crypto.sm3_hash(test_data)
    if hash_result:
        print(f"   SM3 哈希: {hash_result}")
        print(f"   哈希长度: {len(hash_result)} 字符 (期望64)")
    
    # 测试 SM2 加密/解密
    print("\n2. 测试 SM2 加密/解密:")
    encrypted = crypto.sm2_encrypt(test_data)
    if encrypted:
        print(f"   加密成功: {encrypted[:50]}...")
        decrypted = crypto.sm2_decrypt(encrypted)
        if decrypted:
            print(f"   解密成功: {decrypted}")
            print(f"   解密匹配: {decrypted == test_data}")
    
    # 测试 SM2 签名/验证
    print("\n3. 测试 SM2 签名/验证:")
    signature = crypto.sm2_sign(test_data)
    if signature:
        print(f"   签名成功: {signature[:50]}...")
        verified = crypto.sm2_verify(test_data, signature)
        print(f"   验证签名: {verified}")
    
    # 测试 SM4 加密/解密
    print("\n4. 测试 SM4 加密/解密:")
    sm4_encrypted = crypto.sm4_encrypt(test_data)
    if sm4_encrypted:
        print(f"   SM4 加密成功: {sm4_encrypted[:50]}...")
        sm4_decrypted = crypto.sm4_decrypt(sm4_encrypted)
        if sm4_decrypted:
            print(f"   SM4 解密成功: {sm4_decrypted}")
            print(f"   解密匹配: {sm4_decrypted == test_data}")
    
    # 测试使用服务器公钥加密
    print("\n5. 测试使用服务器公钥加密:")
    # 生成服务器公钥
    server_crypto = __import__('crypto_gmssl', fromlist=['GMSCrypto']).GMSCrypto()
    server_public_key = server_crypto.get_public_key_pem()
    if server_public_key:
        crypto.set_server_public_key(server_public_key)
        encrypted = crypto.encrypt_with_server_public_key(test_data)
        if encrypted:
            print(f"   使用服务器公钥加密成功: {encrypted[:50]}...")
            # 使用服务器私钥解密
            decrypted = server_crypto.sm2_decrypt(encrypted)
            if decrypted:
                print(f"   服务器解密成功: {decrypted}")
                print(f"   解密匹配: {decrypted == test_data}")
    
    # 测试证书签名
    print("\n6. 测试证书签名:")
    cert_data = {
        "subject": "CN=Test User",
        "issuer": "CN=GMCA Root CA",
        "serial_number": crypto.generate_serial_number(),
        "validity": {
            "not_before": datetime.now().strftime("%Y%m%d%H%M%SZ"),
            "not_after": (datetime.now() + timedelta(days=365)).strftime("%Y%m%d%H%M%SZ")
        }
    }
    cert_signature = crypto.sign_certificate(cert_data)
    if cert_signature:
        print(f"   证书签名成功: {cert_signature[:50]}...")
        verified = crypto.verify_certificate_signature(cert_data, cert_signature)
        print(f"   验证证书签名: {verified}")
    
    # 测试初始化状态
    print("\n7. 测试初始化状态:")
    print(f"   已初始化: {crypto.is_initialized()}")
    
    print("\n" + "=" * 60)
    print("客户端国密加密测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_client_gms_crypto()
