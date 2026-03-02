from typing import Dict, Optional, List
from datetime import datetime

class DatabaseInterface:
    def add_certificate(self, serial_number: str, subject_name: str, public_key: str,
                       issue_date: datetime, expiry_date: datetime, signature: str) -> bool:
        """添加证书到数据库"""
        pass

    def verify_certificate(self, serial_number: str) -> Optional[Dict]:
        """验证证书"""
        pass

    def revoke_certificate(self, serial_number: str) -> bool:
        """撤销证书"""
        pass

    def add_user(self, username: str, password_hash: str, role: str = 'user') -> bool:
        """添加用户"""
        pass

    def verify_user(self, username: str, password_hash: str) -> Optional[Dict]:
        """验证用户"""
        # 这是接口方法，子类应该实现此方法
        # 提供一个安全的默认实现，避免空方法导致的问题
        try:
            print(f"警告: DatabaseInterface.verify_user被调用但未被实现")
            return None
        except Exception as e:
            print(f"DatabaseInterface.verify_user出现异常: {str(e)}")
            return None

    def update_user(self, user_id: int, password_hash: Optional[str] = None, role: Optional[str] = None) -> bool:
        """更新用户信息"""
        pass

    def create_certificate_template(self, name: str, validity_period: int, key_usage: str, allowed_roles: str = 'admin,user') -> Optional[int]:
        """创建证书模板"""
        pass

    def update_certificate_template(self, template_id: int, name: Optional[str] = None,
                                  validity_period: Optional[int] = None, key_usage: Optional[str] = None,
                                  allowed_roles: Optional[str] = None) -> bool:
        """更新证书模板"""
        pass

    def set_template_permission(self, template_id: int, user_id: int, can_use: bool = True) -> bool:
        """设置模板权限"""
        pass
        
    def get_certificate_templates(self) -> List[Dict]:
        """获取证书模板列表"""
        pass