import os
import json
import time
import base64
import uuid
import yaml
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Dict, Optional, Any, List, Union

# 导入国密加密工具
from crypto_gmssl import GMSCrypto

class SecureLoggerManager:
    """安全日志管理器
    
    实现功能：
    1. 实时捕获证书生命周期关键事件
    2. 记录审核节点、SM2签发参数、时间戳和证书SM3哈希值
    3. 记录管理员认证信息和配置修改
    4. 通过SM3哈希值防止日志篡改
    5. 使用SM4-CBC加密存储敏感字段
    6. 实现审计员认证后的解密查看机制
    """
    
    def __init__(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(script_dir))
        self.config_path = os.path.join(project_root, 'config', 'database', 'config.yaml')
        self.logger = None
        self.ui_callback = None
        self.crypto = GMSCrypto()
        self.log_dir = Path(script_dir) / "logs"
        self.log_dir.mkdir(exist_ok=True)
        self.secure_log_file = self.log_dir / "secure_log.json"
        self.audit_log_file = self.log_dir / "audit_log.json"
        self.cert_log_file = self.log_dir / "certificate_log.json"
        self.admin_log_file = self.log_dir / "admin_log.json"
        
        # 初始化日志文件
        for log_file in [self.secure_log_file, self.audit_log_file, self.cert_log_file, self.admin_log_file]:
            if not log_file.exists():
                with open(log_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
        
        # 初始化标准日志记录器
        self.init_logger()
    
    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"加载日志配置文件失败: {str(e)}")
            # 返回默认配置
            return {
                'logging': {
                    'level': 'INFO',
                    'file': 'ca.log',
                    'max_size': 10485760,
                    'backup_count': 5
                },
                'security': {
                    'encrypt_sensitive_fields': True,
                    'hash_verification': True,
                    'audit_role': 'auditor'
                }
            }
    
    def init_logger(self):
        """初始化标准日志记录器"""
        try:
            config = self.load_config()
            log_config = config.get('logging', {})
            
            # 创建日志目录
            log_dir = self.log_dir
            log_file = log_dir / log_config.get('file', 'ca.log')
            
            # 配置日志处理器
            self.logger = logging.getLogger('CA')
            self.logger.setLevel(getattr(logging, log_config.get('level', 'INFO')))
            
            # 如果已经初始化过，直接返回
            if self.logger.handlers:
                return
            
            # 添加控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '[%(asctime)s] %(levelname)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            self.logger.addHandler(console_handler)
            
            # 文件处理器
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=log_config.get('max_size', 10485760),
                backupCount=log_config.get('backup_count', 5),
                encoding='utf-8'
            )
            file_handler.setFormatter(logging.Formatter(
                '[%(asctime)s] %(levelname)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            self.logger.addHandler(file_handler)
            
        except Exception as e:
            print(f"初始化日志系统失败: {str(e)}")
            raise
    
    def get_logger(self):
        """返回已初始化的logger实例"""
        if not self.logger:
            self.init_logger()
        return self.logger
    
    def log(self, message, level='info'):
        """记录普通日志"""
        if not self.logger:
            return
        
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        log_func(message)
    
    def _calculate_hash(self, data: Dict) -> str:
        """计算日志条目的SM3哈希值"""
        # 将数据转换为JSON字符串
        json_str = json.dumps(data, sort_keys=True)
        # 计算SM3哈希
        return self.crypto.sm3_hash(json_str)
    
    def _encrypt_sensitive_field(self, value: str) -> str:
        """使用SM4-CBC加密敏感字段"""
        try:
            # 确保SM4密钥已生成
            if not hasattr(self.crypto, 'sm4_key_file') or not self.crypto.sm4_key_file.exists():
                self.crypto.generate_sm4_key()
            
            # 将值转换为字符串
            if not isinstance(value, str):
                value = str(value)
            
            # 使用SM4加密
            encrypted_data = self.crypto.sm4_encrypt(value)
            if encrypted_data:
                return f"ENCRYPTED:{encrypted_data}"
            return value
        except Exception as e:
            self.log(f"加密敏感字段失败: {str(e)}", 'error')
            return f"ENCRYPTION_FAILED:{value}"
    
    def _decrypt_sensitive_field(self, encrypted_value: str, auditor_id: str = None) -> str:
        """解密敏感字段，需要审计员权限"""
        try:
            # 验证审计员权限（实际应用中应该有更严格的验证）
            if not auditor_id:
                return "[需要审计员权限]"
            
            # 检查是否是加密值
            if not encrypted_value.startswith("ENCRYPTED:"):
                return encrypted_value
            
            # 提取加密数据
            encrypted_data = encrypted_value[len("ENCRYPTED:"):]
            
            # 使用SM4解密
            decrypted_data = self.crypto.sm4_decrypt(encrypted_data)
            if decrypted_data and 'value' in decrypted_data:
                return decrypted_data['value']
            return "[解密失败]"
        except Exception as e:
            self.log(f"解密敏感字段失败: {str(e)}", 'error')
            return "[解密失败]"
    
    def _load_log_file(self, log_file: Path) -> List[Dict]:
        """加载日志文件内容"""
        try:
            if not log_file.exists():
                return []
            with open(log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.log(f"加载日志文件失败: {str(e)}", 'error')
            return []
    
    def _save_log_file(self, log_file: Path, log_entries: List[Dict]):
        """保存日志文件内容"""
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(log_entries, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log(f"保存日志文件失败: {str(e)}", 'error')
    
    def _append_log_entry(self, log_file: Path, log_entry: Dict):
        """添加日志条目到日志文件"""
        log_entries = self._load_log_file(log_file)
        log_entries.append(log_entry)
        self._save_log_file(log_file, log_entries)
    
    def log_certificate_event(self, event_type: str, certificate_data: Dict, sensitive_fields: List[str] = None):
        """记录证书生命周期事件
        
        Args:
            event_type: 事件类型，如'申请'、'签发'、'撤销'等
            certificate_data: 证书相关数据
            sensitive_fields: 需要加密的敏感字段列表
        """
        try:
            # 默认敏感字段
            if sensitive_fields is None:
                sensitive_fields = ['subject_key', 'issuer_key']
            
            # 创建日志条目
            log_entry = {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.now().isoformat(),
                'event_type': event_type,
                'certificate': {}
            }
            
            # 处理证书数据，加密敏感字段
            for key, value in certificate_data.items():
                if key in sensitive_fields:
                    log_entry['certificate'][key] = self._encrypt_sensitive_field(value)
                else:
                    log_entry['certificate'][key] = value
            
            # 如果是签发事件，记录SM2算法参数和证书哈希值
            if event_type == '签发':
                # 记录SM2签名参数（实际应用中应从签名过程中获取）
                log_entry['signature_params'] = {
                    'algorithm': 'SM2 with SM3',
                    'key_size': '256 bits'
                }
                
                # 计算证书内容的SM3哈希值
                if 'content' in certificate_data:
                    cert_content = certificate_data['content']
                    log_entry['certificate']['sm3_hash'] = self.crypto.sm3_hash(cert_content)
            
            # 计算日志条目的哈希值
            log_entry['hash'] = self._calculate_hash(log_entry)
            
            # 保存到证书日志文件
            self._append_log_entry(self.cert_log_file, log_entry)
            
            # 同时记录到标准日志
            self.log(f"证书事件: {event_type}, 序列号: {certificate_data.get('serial_number', 'N/A')}")
            
            return True
        except Exception as e:
            self.log(f"记录证书事件失败: {str(e)}", 'error')
            return False
    
    def log_admin_event(self, admin_id: str, event_type: str, details: Dict = None, sensitive_fields: List[str] = None):
        """记录管理员操作事件
        
        Args:
            admin_id: 管理员ID
            event_type: 事件类型，如'登录'、'登出'、'配置修改'等
            details: 事件详情
            sensitive_fields: 需要加密的敏感字段列表
        """
        try:
            # 默认敏感字段
            if sensitive_fields is None:
                sensitive_fields = ['ip_address', 'session_key']
            
            # 创建日志条目
            log_entry = {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.now().isoformat(),
                'admin_id': admin_id,
                'event_type': event_type,
                'details': {}
            }
            
            # 处理详情数据，加密敏感字段
            if details:
                for key, value in details.items():
                    if key in sensitive_fields:
                        log_entry['details'][key] = self._encrypt_sensitive_field(value)
                    else:
                        log_entry['details'][key] = value
            
            # 计算日志条目的哈希值
            log_entry['hash'] = self._calculate_hash(log_entry)
            
            # 保存到管理员日志文件
            self._append_log_entry(self.admin_log_file, log_entry)
            
            # 同时记录到标准日志
            self.log(f"管理员事件: {admin_id}, {event_type}")
            
            return True
        except Exception as e:
            self.log(f"记录管理员事件失败: {str(e)}", 'error')
            return False
    
    def log_config_change(self, admin_id: str, config_file: str, changes: Dict):
        """记录配置文件修改
        
        Args:
            admin_id: 管理员ID
            config_file: 配置文件名
            changes: 修改内容，格式为 {'字段': {'old': 旧值, 'new': 新值}}
        """
        details = {
            'config_file': config_file,
            'changes': changes
        }
        return self.log_admin_event(admin_id, '配置修改', details)
    
    def log_audit_event(self, auditor_id: str, action: str, target: str, result: str):
        """记录审计事件
        
        Args:
            auditor_id: 审计员ID
            action: 审计操作，如'查看日志'、'导出日志'等
            target: 审计目标，如'证书日志'、'管理员日志'等
            result: 操作结果，如'成功'、'失败'等
        """
        try:
            # 创建日志条目
            log_entry = {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.now().isoformat(),
                'auditor_id': auditor_id,
                'action': action,
                'target': target,
                'result': result
            }
            
            # 计算日志条目的哈希值
            log_entry['hash'] = self._calculate_hash(log_entry)
            
            # 保存到审计日志文件
            self._append_log_entry(self.audit_log_file, log_entry)
            
            # 同时记录到标准日志
            self.log(f"审计事件: {auditor_id}, {action}, {target}, {result}")
            
            return True
        except Exception as e:
            self.log(f"记录审计事件失败: {str(e)}", 'error')
            return False
    
    def verify_log_integrity(self, log_file: Path) -> Dict[str, Any]:
        """验证日志完整性
        
        检查日志文件中的每个条目的哈希值是否正确，以验证日志是否被篡改
        
        Returns:
            验证结果，包含是否通过、错误条目数量和详情
        """
        try:
            log_entries = self._load_log_file(log_file)
            result = {
                'verified': True,
                'total_entries': len(log_entries),
                'invalid_entries': 0,
                'details': []
            }
            
            for i, entry in enumerate(log_entries):
                # 保存原始哈希值
                original_hash = entry.get('hash')
                if not original_hash:
                    result['verified'] = False
                    result['invalid_entries'] += 1
                    result['details'].append({
                        'index': i,
                        'id': entry.get('id', 'unknown'),
                        'error': '缺少哈希值'
                    })
                    continue
                
                # 移除哈希值后重新计算
                entry_copy = entry.copy()
                entry_copy.pop('hash', None)
                calculated_hash = self._calculate_hash(entry_copy)
                
                # 比较哈希值
                if original_hash != calculated_hash:
                    result['verified'] = False
                    result['invalid_entries'] += 1
                    result['details'].append({
                        'index': i,
                        'id': entry.get('id', 'unknown'),
                        'error': '哈希值不匹配',
                        'original_hash': original_hash,
                        'calculated_hash': calculated_hash
                    })
            
            return result
        except Exception as e:
            self.log(f"验证日志完整性失败: {str(e)}", 'error')
            return {
                'verified': False,
                'error': str(e)
            }
    
    def get_certificate_logs(self, auditor_id: str = None, filters: Dict = None) -> List[Dict]:
        """获取证书日志，支持过滤和解密
        
        Args:
            auditor_id: 审计员ID，用于解密敏感字段
            filters: 过滤条件，如{'event_type': '签发', 'serial_number': 'xxx'}
        
        Returns:
            符合条件的日志条目列表
        """
        try:
            # 记录审计事件
            if auditor_id:
                self.log_audit_event(auditor_id, '查看日志', '证书日志', '成功')
            
            # 加载日志文件
            log_entries = self._load_log_file(self.cert_log_file)
            
            # 应用过滤条件
            if filters:
                filtered_entries = []
                for entry in log_entries:
                    match = True
                    for key, value in filters.items():
                        if key == 'serial_number':
                            # 特殊处理证书序列号
                            if 'certificate' in entry and 'serial_number' in entry['certificate']:
                                if entry['certificate']['serial_number'] != value:
                                    match = False
                                    break
                            else:
                                match = False
                                break
                        elif key not in entry or entry[key] != value:
                            match = False
                            break
                    if match:
                        filtered_entries.append(entry)
                log_entries = filtered_entries
            
            # 解密敏感字段（如果有审计员ID）
            if auditor_id:
                for entry in log_entries:
                    if 'certificate' in entry:
                        for key, value in entry['certificate'].items():
                            if isinstance(value, str) and value.startswith("ENCRYPTED:"):
                                entry['certificate'][key] = self._decrypt_sensitive_field(value, auditor_id)
            
            return log_entries
        except Exception as e:
            self.log(f"获取证书日志失败: {str(e)}", 'error')
            return []
    
    def get_admin_logs(self, auditor_id: str = None, filters: Dict = None) -> List[Dict]:
        """获取管理员日志，支持过滤和解密
        
        Args:
            auditor_id: 审计员ID，用于解密敏感字段
            filters: 过滤条件，如{'admin_id': 'xxx', 'event_type': '登录'}
        
        Returns:
            符合条件的日志条目列表
        """
        try:
            # 记录审计事件
            if auditor_id:
                self.log_audit_event(auditor_id, '查看日志', '管理员日志', '成功')
            
            # 加载日志文件
            log_entries = self._load_log_file(self.admin_log_file)
            
            # 应用过滤条件
            if filters:
                filtered_entries = []
                for entry in log_entries:
                    match = True
                    for key, value in filters.items():
                        if key not in entry or entry[key] != value:
                            match = False
                            break
                    if match:
                        filtered_entries.append(entry)
                log_entries = filtered_entries
            
            # 解密敏感字段（如果有审计员ID）
            if auditor_id:
                for entry in log_entries:
                    if 'details' in entry:
                        for key, value in entry['details'].items():
                            if isinstance(value, str) and value.startswith("ENCRYPTED:"):
                                entry['details'][key] = self._decrypt_sensitive_field(value, auditor_id)
            
            return log_entries
        except Exception as e:
            self.log(f"获取管理员日志失败: {str(e)}", 'error')
            return []
    
    def export_logs(self, auditor_id: str, log_type: str, output_file: str, decrypt: bool = False) -> bool:
        """导出日志文件
        
        Args:
            auditor_id: 审计员ID
            log_type: 日志类型，如'certificate'、'admin'、'audit'、'all'
            output_file: 输出文件路径
            decrypt: 是否解密敏感字段
        
        Returns:
            导出是否成功
        """
        try:
            # 记录审计事件
            self.log_audit_event(auditor_id, '导出日志', f'{log_type}日志', '进行中')
            
            # 确定要导出的日志文件
            log_files = []
            if log_type == 'certificate':
                log_files = [self.cert_log_file]
            elif log_type == 'admin':
                log_files = [self.admin_log_file]
            elif log_type == 'audit':
                log_files = [self.audit_log_file]
            elif log_type == 'all':
                log_files = [self.cert_log_file, self.admin_log_file, self.audit_log_file]
            else:
                self.log(f"未知的日志类型: {log_type}", 'error')
                self.log_audit_event(auditor_id, '导出日志', f'{log_type}日志', '失败')
                return False
            
            # 合并日志
            all_logs = {}
            for log_file in log_files:
                log_name = log_file.stem
                log_entries = self._load_log_file(log_file)
                
                # 解密敏感字段（如果需要）
                if decrypt:
                    for entry in log_entries:
                        # 处理证书日志
                        if 'certificate' in entry:
                            for key, value in entry['certificate'].items():
                                if isinstance(value, str) and value.startswith("ENCRYPTED:"):
                                    entry['certificate'][key] = self._decrypt_sensitive_field(value, auditor_id)
                        
                        # 处理管理员日志
                        if 'details' in entry:
                            for key, value in entry['details'].items():
                                if isinstance(value, str) and value.startswith("ENCRYPTED:"):
                                    entry['details'][key] = self._decrypt_sensitive_field(value, auditor_id)
                
                all_logs[log_name] = log_entries
            
            # 导出到文件
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_logs, f, indent=2, ensure_ascii=False)
            
            # 记录成功事件
            self.log_audit_event(auditor_id, '导出日志', f'{log_type}日志', '成功')
            return True
        except Exception as e:
            self.log(f"导出日志失败: {str(e)}", 'error')
            self.log_audit_event(auditor_id, '导出日志', f'{log_type}日志', f'失败: {str(e)}')
            return False

# 创建全局实例
secure_logger_manager = SecureLoggerManager()