import os
import base64
import json
import subprocess
import secrets
import tempfile
import time
from pathlib import Path
from typing import Tuple, Optional

class CryptoManager:
    def __init__(self):
        # 配置路径
        self.key_dir = Path.home() / ".ca_client"
        self.key_dir.mkdir(exist_ok=True)
        
        # 密钥文件路径
        self.sm2_private_key = self.key_dir / "client.key"
        self.sm2_public_key = self.key_dir / "client.pem"
        self.sm4_key_file = self.key_dir / "sm4.key"
        
        # 密码配置
        self.sm2_password = "password"  # 生产环境应从安全存储获取

    def _run_gmssl(self, args: list, input_data: bytes = None) -> Tuple[bool, bytes]:
        """执行gmssl命令行工具"""
        try:
            result = subprocess.run(
                ["C:\\Program Files (x86)\\GmSSL\\bin\\gmssl.exe"] + args,
                input=input_data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode("gbk", errors="ignore")
            print(f"GmSSL命令执行失败: {' '.join(args)}\n错误信息: {error_msg}")
            return False, b""

    def init_crypto(self):
        """初始化加密工具"""
        try:
            # 检查密钥是否存在，不存在则生成
            if not self.sm2_private_key.exists() or not self.sm2_public_key.exists():
                if not self.generate_sm2_key_pair():
                    return False
            
            # 检查SM4密钥是否存在，不存在则生成
            if not self.sm4_key_file.exists():
                if not self.generate_sm4_key():
                    return False
                    
            return True
        except Exception as e:
            print(f"初始化加密工具失败: {str(e)}")
            return False

    def generate_sm2_key_pair(self) -> bool:
        """生成SM2密钥对"""
        # 生成私钥
        success, _ = self._run_gmssl([
            "sm2", "-genkey",
            "-out", str(self.sm2_private_key),
            "-passout", f"pass:{self.sm2_password}"
        ])
        if not success:
            return False

        # 导出公钥
        success = self._run_gmssl([
            "sm2", "-pubout",
            "-in", str(self.sm2_private_key),
            "-out", str(self.sm2_public_key),
            "-passin", f"pass:{self.sm2_password}"
        ])[0]
        
        if success:
            print("已生成并保存新的SM2密钥对")
        
        return success

    def sm2_encrypt(self, plaintext: str) -> Optional[str]:
        """SM2加密"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(plaintext.encode() if isinstance(plaintext, str) else plaintext)
            tmp_path = tmp.name

        success, output = self._run_gmssl([
            "sm2utl", "-encrypt",
            "-pubin", "-inkey", str(self.sm2_public_key),
            "-in", tmp_path
        ])

        os.remove(tmp_path)
        return base64.b64encode(output).decode() if success else None

    def sm2_decrypt(self, ciphertext: str) -> Optional[str]:
        """SM2解密"""
        cipher_data = base64.b64decode(ciphertext)
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(cipher_data)
            tmp_path = tmp.name

        success, output = self._run_gmssl([
            "sm2utl", "-decrypt",
            "-inkey", str(self.sm2_private_key),
            "-passin", f"pass:{self.sm2_password}",
            "-in", tmp_path
        ])

        os.remove(tmp_path)
        return output.decode(errors="ignore") if success else None

    def generate_sm4_key(self) -> bool:
        """生成SM4密钥"""
        key = secrets.token_bytes(16)
        self.sm4_key_file.write_bytes(key)
        print("已生成并保存新的SM4密钥")
        return True
        
    def get_or_generate_sm4_key(self) -> bytes:
        """获取或生成SM4会话密钥
        
        如果会话密钥已存在，则直接返回；否则生成新的会话密钥
        
        Returns:
            SM4会话密钥
        """
        if not self.sm4_key_file.exists() or self.sm4_key_file.stat().st_size == 0:
            self.generate_sm4_key()
            
        return self.sm4_key_file.read_bytes()
        
    def encrypt_session_key(self, server_public_key):
        """使用服务器公钥加密会话密钥
        
        Args:
            server_public_key: 服务器的SM2公钥
            
        Returns:
            加密后的会话密钥的Base64编码，失败返回None
        """
        try:
            # 确保SM4密钥已生成并获取密钥内容
            sm4_key = self.get_or_generate_sm4_key()
            
            # 创建keys文件夹（如果不存在）
            keys_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "keys"
            keys_dir.mkdir(exist_ok=True)
            
            # 将SM4密钥保存到keys文件夹中
            session_key_path = keys_dir / "session_key.key"
            with open(session_key_path, 'wb') as f:
                f.write(sm4_key)
            
            # 处理服务器公钥中的\n字符
            if "\\n" in server_public_key:
                server_public_key = server_public_key.replace("\\n", "\n")
            
            # 将服务器公钥保存到临时文件中
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pem') as pubkey_tmp:
                pubkey_tmp.write(server_public_key.encode())
                server_pubkey_file = pubkey_tmp.name
            
            # 打印调试信息
            print(f"服务器公钥: {server_public_key[:30]}...")
            print(f"SM4密钥长度: {len(sm4_key)} 字节")
            print(f"服务器公钥临时文件路径: {server_pubkey_file}")
            
            # 创建输出文件
            output_file = keys_dir / "encrypted_session_key.bin"
            
            # 将SM4密钥写入临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix='.key') as tmp:
                tmp.write(sm4_key)
                tmp_path = tmp.name
            
            print(f"SM4密钥已写入临时文件: {tmp_path}，准备加密")
            
            # 最多重试3次
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # 使用_run_gmssl方法直接加密
                    success, encrypted_data = self._run_gmssl([
                        "pkeyutl", "-encrypt",
                        "-pubin", "-inkey", server_pubkey_file,
                        "-pkeyopt", "enc-scheme:sm2",
                        "-in", tmp_path
                    ])
                    
                    if success and encrypted_data and len(encrypted_data) > 0:
                        print(f"SM2加密成功，加密结果大小: {len(encrypted_data)} 字节")
                        break
                except Exception as e:
                    print(f"SM2加密尝试 {retry_count + 1}/{max_retries} 失败: {str(e)}")
                
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(1)  # 添加重试延迟
                
                # 删除临时文件
                try:
                    os.remove(tmp_path)
                except Exception as e:
                    print(f"删除临时文件失败: {str(e)}")
                
                if retry_count < max_retries:
                    # 重新创建临时文件
                    with tempfile.NamedTemporaryFile(delete=False) as tmp:
                        tmp.write(sm4_key)
                        tmp_path = tmp.name
            
            if not success or not encrypted_data or len(encrypted_data) == 0:
                print("SM2加密失败或加密结果为空，已重试最大次数")
                return None
                
            # 将加密结果写入输出文件
            with open(output_file, 'wb') as f:
                f.write(encrypted_data)
                
            print(f"SM4密钥加密成功，加密结果大小: {len(encrypted_data)} 字节")
            
            # 读取加密后的数据
            with open(output_file, 'rb') as f:
                encrypted_data = f.read()
                
            # 返回Base64编码的加密数据
            return base64.b64encode(encrypted_data).decode('utf-8')

        except Exception as e:
            print(f"会话密钥加密失败: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # 即使出现异常，也检查一下是否已经生成了加密文件
            output_file = Path(os.path.dirname(os.path.abspath(__file__))) / "keys" / "encrypted_session_key.bin"
            if output_file.exists() and output_file.stat().st_size > 0:
                print(f"尽管发生异常，但检测到已存在的加密会话密钥文件: {output_file}")
                
                # 读取已存在的加密数据
                with open(output_file, 'rb') as f:
                    encrypted_data = f.read()
                
                print(f"使用已存在的加密会话密钥，大小: {len(encrypted_data)} 字节")
                return base64.b64encode(encrypted_data).decode('utf-8')
                
            return None
            
    def _save_temp_file(self, content):
        """保存内容到临时文件并返回文件路径"""
        temp_file = tempfile.mktemp()
        with open(temp_file, 'wb') as f:
            f.write(content)
        return temp_file
        
    def _cleanup_temp_files(self, file_list):
        """清理临时文件"""
        for file_path in file_list:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"删除临时文件失败: {file_path}, 错误: {str(e)}")

    def sm4_encrypt(self, data: dict) -> Optional[str]:
        """SM4-CBC加密数据"""
        if not self.sm4_key_file.exists():
            return None

        key = self.sm4_key_file.read_bytes()
        iv = secrets.token_bytes(16)

        # 序列化数据
        json_data = json.dumps(data).encode()
        
        # 加密
        with tempfile.NamedTemporaryFile(delete=False) as tmp_in:
            tmp_in.write(json_data)
            tmp_in_path = tmp_in.name

        success, output = self._run_gmssl([
            "sms4", "-e",
            "-K", key.hex(),
            "-iv", iv.hex(),
            "-in", tmp_in_path
        ])

        os.remove(tmp_in_path)
        if not success:
            return None

        # 返回格式: IV + 密文
        return base64.b64encode(iv + output).decode()

    def sm4_decrypt(self, ciphertext: str) -> Optional[dict]:
        """SM4-CBC解密数据"""
        if not self.sm4_key_file.exists():
            return None

        key = self.sm4_key_file.read_bytes()
        full_data = base64.b64decode(ciphertext)
        iv, cipher_data = full_data[:16], full_data[16:]

        with tempfile.NamedTemporaryFile(delete=False) as tmp_out:
            tmp_out.write(cipher_data)
            tmp_out_path = tmp_out.name

        success, output = self._run_gmssl([
            "sms4", "-d",
            "-K", key.hex(),
            "-iv", iv.hex(),
            "-in", tmp_out_path
        ])

        os.remove(tmp_out_path)
        return json.loads(output.decode()) if success else None

    def sm3_hash(self, data: str) -> str:
        """计算SM3哈希"""
        try:
            result = subprocess.run(
                ["echo", "-n", data],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True
            )
            if result.returncode != 0:
                print(f"Echo命令执行失败: {result.stderr.decode('gbk', errors='ignore')}")
                return ""
                
            result = subprocess.run(
                ["C:\\Program Files (x86)\\GmSSL\\bin\\gmssl.exe", "sm3"],
                input=result.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if result.returncode != 0:
                print(f"GmSSL命令执行失败: {result.stderr.decode('gbk', errors='ignore')}")
                return ""
                
            output = result.stdout.decode(errors='ignore')
            return output.split("=")[1].strip()
        except Exception as e:
            print(f"SM3哈希计算失败: {str(e)}")
            return ""
            
    def sm2_sign(self, data: str) -> Optional[str]:
        """使用SM2私钥对数据进行签名
        
        Args:
            data: 要签名的数据
            
        Returns:
            成功返回Base64编码的签名，失败返回None
        """
        try:
            # 确保密钥目录和私钥文件存在
            self.key_dir.mkdir(exist_ok=True)
            
            if not self.sm2_private_key.exists():
                print(f"SM2私钥文件不存在: {self.sm2_private_key}")
                if not self.generate_sm2_key_pair():
                    print("生成SM2密钥对失败")
                    return None
            
            # 将数据写入临时文件
            with tempfile.NamedTemporaryFile(delete=False) as tmp_data:
                tmp_data.write(data.encode())
                tmp_data_path = tmp_data.name
            
            # 计算SM3哈希值并保存到临时文件
            hash_file = tempfile.NamedTemporaryFile(delete=False)
            hash_file_path = hash_file.name
            hash_file.close()
            
            success, _ = self._run_gmssl([
                "sm3", "-binary",
                "-out", hash_file_path,
                tmp_data_path
            ])
            
            if not success:
                os.remove(tmp_data_path)
                os.remove(hash_file_path)
                print("计算SM3哈希值失败")
                return None
            
            # 使用pkeyutl对哈希值进行签名
            success, output = self._run_gmssl([
                "pkeyutl", "-sign",
                "-in", hash_file_path,
                "-inkey", str(self.sm2_private_key),
                "-passin", f"pass:{self.sm2_password}"
            ])
            
            # 清理临时文件
            os.remove(tmp_data_path)
            os.remove(hash_file_path)
            
            if not success:
                print("SM2签名失败")
                return None
                
            return base64.b64encode(output).decode()
        except Exception as e:
            print(f"SM2签名过程发生错误: {str(e)}")
            return None

    def is_initialized(self) -> bool:
        """检查加密模块是否已初始化"""
        return self.sm2_private_key.exists() and self.sm2_public_key.exists() and self.sm4_key_file.exists()

    def load_or_generate_sm2_key_pair(self) -> Tuple[str, str]:
        """加载或生成SM2密钥对，并返回私钥和公钥内容"""
        # 检查密钥是否存在且不为空
        if not self.sm2_private_key.exists() or not self.sm2_public_key.exists() or self.sm2_private_key.stat().st_size == 0 or self.sm2_public_key.stat().st_size == 0:
            # 密钥不存在或为空，生成新密钥对
            if not self.generate_sm2_key_pair():
                raise Exception("生成SM2密钥对失败")
        
        # 读取公钥内容
        public_key = self.sm2_public_key.read_text(errors='ignore')
        # 私钥内容通常不直接读取，这里仅返回文件路径作为标识
        private_key = str(self.sm2_private_key)
        
        return private_key, public_key
        
    def generate_certificate_request(self, subject_name: str) -> Optional[str]:
        """生成证书申请请求(CSR)
        
        Args:
            subject_name: 证书主题名称，格式如 "CN=张三,O=示例公司,C=CN"
            
        Returns:
            成功返回CSR内容（PEM格式），失败返回None
        """
        # 确保密钥对已存在
        if not self.sm2_private_key.exists() or not self.sm2_public_key.exists():
            if not self.generate_sm2_key_pair():
                return None
                
        # 创建临时CSR文件
        csr_file = self.key_dir / "temp.csr"
        
        # 将逗号分隔的主题名称转换为斜杠分隔的格式
        # 例如："CN=张三,O=示例公司,C=CN" -> "/CN=张三/O=示例公司/C=CN"
        formatted_subject = ""
        parts = subject_name.split(",")
        for part in parts:
            if "=" in part:
                key, value = part.split("=", 1)
                # 对值进行转义
                escaped_value = value.replace(" ", "\ ")  # 转义空格
                escaped_value = escaped_value.replace(",", "\,")  # 转义逗号
                escaped_value = escaped_value.replace("+", "\+")  # 转义加号
                escaped_value = escaped_value.replace("<", "\<")  # 转义小于号
                escaped_value = escaped_value.replace(">", "\>")  # 转义大于号
                escaped_value = escaped_value.replace(";", "\;")  # 转义分号
                formatted_subject += f"/{key}={escaped_value}"
            else:
                formatted_subject += f"/{part}"
        
        print(f"原始主题名称: {subject_name}")
        print(f"格式化后主题名称: {formatted_subject}")
        
        # 使用GmSSL生成证书请求
        success, _ = self._run_gmssl([
            "req", "-new",
            "-key", str(self.sm2_private_key),
            "-out", str(csr_file),
            "-subj", formatted_subject,
            "-passin", f"pass:{self.sm2_password}"
        ])
        
        if not success or not csr_file.exists():
            print(f"生成证书请求失败")
            return None
            
        # 读取CSR内容
        csr_content = csr_file.read_text(errors='ignore')
        
        # 删除临时文件
        try:
            csr_file.unlink()
        except Exception as e:
            print(f"删除临时CSR文件失败: {str(e)}")
            
        return csr_content
        
    def save_certificate(self, cert_content: str, cert_path: Optional[str] = None) -> bool:
        """保存证书
        
        Args:
            cert_content: 证书内容（PEM格式）
            cert_path: 证书保存路径，如果为None则使用默认路径
            
        Returns:
            保存成功返回True，否则返回False
        """
        try:
            # 如果未指定路径，使用默认路径
            if cert_path is None:
                cert_dir = self.key_dir / "certificates"
                cert_dir.mkdir(exist_ok=True)
                cert_path = cert_dir / "client.crt"
            else:
                cert_path = Path(cert_path)
                cert_path.parent.mkdir(exist_ok=True)
                
            # 写入证书内容
            with open(cert_path, 'w') as f:
                f.write(cert_content)
                
            print(f"证书已保存到: {cert_path}")
            return True
        except Exception as e:
            print(f"保存证书失败: {str(e)}")
            return False

    # 在CryptoManager类中添加以下方法
    
    def is_server_public_key_exists(self) -> bool:
        """检查服务器公钥是否存在
        
        Returns:
            存在返回True，否则返回False
        """
        keys_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "keys"
        server_pubkey_file = keys_dir / "server_public_key.pem"
        
        # 检查文件是否存在且非空
        return server_pubkey_file.exists() and server_pubkey_file.stat().st_size > 0
    
    def get_server_public_key(self) -> Optional[str]:
        """获取保存的服务器公钥
        
        Returns:
            服务器公钥内容，不存在返回None
        """
        keys_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "keys"
        server_pubkey_file = keys_dir / "server_public_key.pem"
        
        if not server_pubkey_file.exists() or server_pubkey_file.stat().st_size == 0:
            return None
            
        return server_pubkey_file.read_text(errors='ignore')
    
    def save_server_public_key(self, server_public_key: str) -> bool:
        """保存服务器公钥
        
        Args:
            server_public_key: 服务器公钥内容
            
        Returns:
            保存成功返回True，否则返回False
        """
        try:
            # 处理服务器公钥中的\n字符
            if "\\n" in server_public_key:
                server_public_key = server_public_key.replace("\\n", "\n")
            
            # 创建keys文件夹（如果不存在）
            keys_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "keys"
            keys_dir.mkdir(exist_ok=True)
            
            # 将服务器公钥保存到keys文件夹中
            server_pubkey_file = keys_dir / "server_public_key.pem"
            with open(server_pubkey_file, 'w') as f:
                f.write(server_public_key)
                
            print(f"服务器公钥已保存到: {server_pubkey_file}")
            return True
        except Exception as e:
            print(f"保存服务器公钥失败: {str(e)}")
            return False
