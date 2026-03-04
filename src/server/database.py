import logging
import sys
from datetime import datetime
import time
import mysql.connector.pooling
import mysql.connector
from database_interface import DatabaseInterface
from threading import Lock
from typing import Dict, Optional, List
import os

# 导入国密加密工具
try:
    from crypto_gmssl import GMSCrypto
    GMSSL_AVAILABLE = True
except ImportError:
    GMSSL_AVAILABLE = False


class DatabaseManager(DatabaseInterface):
    def __init__(self, log_callback=None):
        self.max_retries = 3
        self.retry_delay = 2
        self.log_callback = log_callback or (lambda x: None)
        self.connection_pool = None
        self._pool_lock = Lock()  # 添加线程安全锁
        self.crypto = None  # 用于密码哈希
        
        try:
            import yaml
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(script_dir))
            config_path = os.path.join(project_root, 'config', 'database', 'config.yaml')
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            db_config = config.get('database', {})
            self.config = {
                'host': db_config.get('host'),
                'port': db_config.get('port', 3306),
                'user': db_config.get('user'),
                'password': db_config.get('password'),
                'database': db_config.get('database'),
                'connection_timeout': db_config.get('connect_timeout', 30),
                'raise_on_warnings': True,
                'get_warnings': True
            }

            required_fields = ['host', 'user', 'password', 'database']
            missing_fields = [field for field in required_fields if not self.config.get(field)]
            if missing_fields:
                raise ValueError(f"缺少必要的数据库配置项: {', '.join(missing_fields)}")

            # 初始化加密工具
            try:
                if GMSSL_AVAILABLE:
                    self.crypto = GMSCrypto()
                else:
                    self.crypto = None
            except Exception as e:
                self.log(f"初始化加密工具失败: {str(e)}")

            self._init_database_with_retry()
        except Exception as e:
            self.log(f"数据库管理器初始化失败: {str(e)}")
            raise

    def log(self, message):
        """统一的日志处理"""
        try:
            if message is None:
                message = "<None>"
            elif not isinstance(message, str):
                message = str(message)
            
            # 只通过回调输出，避免重复
            if self.log_callback and callable(self.log_callback):
                self.log_callback(message)
        except Exception:
            pass


    def _load_db_config(self):
        """加载数据库配置"""
        return {
            'pool_name': 'mypool',
            'pool_size': 10,
            'host': self.config['host'],
            'port': int(self.config.get('port', 3306)),
            'user': self.config['user'],
            'password': self.config['password'],
            'database': self.config['database'],
            'use_pure': True,
            'auth_plugin': 'mysql_native_password',
            'time_zone': '+00:00'  # 强制使用UTC时区
        }

    def _init_connection_pool(self):
        """初始化MySQL连接池"""
        try:
            if self.connection_pool is not None:
                return  # 已存在连接池时直接复用

            self.log("初始化MySQL连接池")
            # 增加连接池配置参数
            db_config = self._load_db_config()

            # 设置连接时区
            connection_params = {
                'host': self.config['host'],
                'port': int(self.config.get('port', 3306)),
                'user': self.config['user'],
                'password': self.config['password'],
                'database': self.config['database'],
                'use_pure': True,
                'auth_plugin': 'mysql_native_password',
                'time_zone': '+00:00'  # 强制使用UTC时区
            }

            # 创建连接池时设置pool_reset_session=False
            self.connection_pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name='mypool',
                pool_size=10,
                **connection_params
            )

            # 测试连接...
            test_conn = None
            try:
                test_conn = self.connection_pool.get_connection()
                if test_conn and test_conn.is_connected():
                    self.log("连接池测试连接成功")
            except Exception as test_err:
                self.log(f"连接池测试连接失败: {str(test_err)}")
                raise
            finally:
                if test_conn:
                    try:
                        if test_conn.is_connected():
                            test_conn.close()
                    except Exception as e:
                        self.log(f"关闭测试连接时出错: {str(e)}")

            self.log("连接池初始化成功")
        except Exception as e:
            self.log(f"连接池初始化失败: {str(e)}")
            # 确保清理任何可能部分初始化的资源
            if hasattr(self, 'connection_pool') and self.connection_pool is not None:
                try:
                    for conn in self.connection_pool._cnx_queue:
                        try:
                            if conn and hasattr(conn, 'is_connected') and conn.is_connected():
                                conn.close()
                        except Exception as close_err:
                            self.log(f"清理连接时出错: {str(close_err)}")
                except Exception as pool_err:
                    self.log(f"清理连接池时出错: {str(pool_err)}")
                finally:
                    self.connection_pool = None
            raise

    def _init_database_with_retry(self):
        """带重试机制的数据库初始化"""
        for attempt in range(self.max_retries):
            try:
                self.log(f"尝试初始化数据库 (尝试 {attempt + 1}/{self.max_retries})")
                self.init_database()
                return
            except mysql.connector.Error as err:
                self.log(f"数据库连接错误: {str(err)}")
                if attempt < self.max_retries - 1:
                    self.log(f"数据库连接失败，{self.retry_delay}秒后重试")
                    time.sleep(self.retry_delay)
                else:
                    self.log("数据库连接重试次数已用完，初始化失败")
                    raise

    def init_database(self):
        """初始化数据库"""
        conn = None
        cursor = None
        try:
            self.log("尝试建立数据库连接...")

            conn = mysql.connector.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                connection_timeout=self.config['connection_timeout'],
                raise_on_warnings=self.config['raise_on_warnings'],
                get_warnings=self.config['get_warnings'],
                use_pure=True,
                auth_plugin='mysql_native_password'
            )
            self.log("成功连接到MySQL服务器")

            cursor = conn.cursor()

            cursor.execute(f"SHOW DATABASES LIKE '{self.config['database']}'")
            if not cursor.fetchone():
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.config['database']}")
                self.log(f"创建数据库 {self.config['database']}")
            else:
                self.log(f"数据库 {self.config['database']} 已存在")

            cursor.execute(f"USE {self.config['database']}")

            self._create_tables(cursor)
            
            conn.commit()
            self.log("数据库初始化成功")

        except mysql.connector.Error as err:
            self.log(f"数据库操作错误: {err}")
            if conn and conn.is_connected():
                conn.rollback()
            raise
        except Exception as e:
            self.log(f"数据库操作失败: {str(e)}")
            raise
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    if conn.is_connected():
                        conn.close()
                except Exception:
                    pass

    def _create_tables(self, cursor):
        """创建数据库表"""
        tables = {
            'certificate_templates': """
                CREATE TABLE IF NOT EXISTS certificate_templates (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    validity_period INT NOT NULL,
                    key_usage VARCHAR(255) NOT NULL,
                    allowed_roles VARCHAR(50) DEFAULT 'admin,user',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """,
            'users': """
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(64) UNIQUE NOT NULL,
                    password_hash VARCHAR(128) NOT NULL,
                    role ENUM('admin', 'user') DEFAULT 'user',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            'key_pairs': """
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
            """,
            'certificates': """
                CREATE TABLE IF NOT EXISTS certificates (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    serial_number VARCHAR(64) UNIQUE NOT NULL,
                    subject_name VARCHAR(255) NOT NULL,
                    public_key_fingerprint VARCHAR(64) NOT NULL,
                    status ENUM('pending', 'valid', 'revoked', 'rejected') DEFAULT 'pending',
                    issue_date DATETIME NOT NULL,
                    expiry_date DATETIME NOT NULL,
                    signature TEXT NOT NULL,
                    template_id INT,
                    organization VARCHAR(255),
                    department VARCHAR(255),
                    email VARCHAR(255),
                    usage_purpose VARCHAR(255),
                    remarks TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (template_id) REFERENCES certificate_templates(id)
                )
            """,
            'template_permissions': """
                CREATE TABLE IF NOT EXISTS template_permissions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    template_id INT NOT NULL,
                    user_id INT NOT NULL,
                    can_use BOOLEAN DEFAULT true,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (template_id) REFERENCES certificate_templates(id),
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE KEY unique_template_user (template_id, user_id)
                )
            """
        }
        
        for table_name, create_sql in tables.items():
            cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
            if not cursor.fetchone():
                cursor.execute(create_sql)
                self.log(f"创建表 {table_name} 成功")
        
        self._add_default_users(cursor)

    def _add_default_users(self, cursor):
        """添加默认用户"""
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            admin_password_hash = self.crypto.sm3_hash('123456')
            user_password_hash = self.crypto.sm3_hash('123456')
            cursor.execute("""
                INSERT INTO users (username, password_hash, role)
                VALUES (%s, %s, 'admin'), (%s, %s, 'user')
            """, ('admin', admin_password_hash, 'user', user_password_hash))
            self.log("添加默认用户成功")

    def get_connection(self):
        """从连接池获取连接，并验证连接有效性"""
        try:
            with self._pool_lock:
                if self.connection_pool is None:
                    self._init_connection_pool()
            conn = self.connection_pool.get_connection()

            # 验证连接有效性
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                # 确保读取结果集
                cursor.fetchall()
                cursor.close()
                return conn
            except mysql.connector.Error:
                self.log("连接失效，尝试重连")
                # 在重连前确保关闭所有游标并消费未读结果集
                try:
                    for c in conn._get_cursor_list():
                        try:
                            if not c._have_unread_result():
                                continue
                            c.fetchall()
                        except:
                            pass
                        finally:
                            c.close()
                except:
                    pass
                
                # 尝试重新连接
                try:
                    conn.reconnect()
                    # 验证重连后的连接
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.fetchall()
                    cursor.close()
                    return conn
                except mysql.connector.Error as reconnect_err:
                    self.log(f"重连失败: {reconnect_err}")
                    raise
        except mysql.connector.Error as err:
            self.log(f"获取连接失败: {err}")
            raise

    def add_certificate(self, serial_number, subject_name, public_key, issue_date, expiry_date, signature, template_id=None):
        """添加证书"""
        # 参数验证
        if not all([serial_number, subject_name, public_key, issue_date, expiry_date, signature]):
            self.log("添加证书失败: 缺少必要参数")
            return False

        # 长度限制
        if len(serial_number) > 64 or len(subject_name) > 255:
            self.log("添加证书失败: 序列号或主题名称超出长度限制")
            return False

        # 日期验证
        if not isinstance(issue_date, datetime) or not isinstance(expiry_date, datetime):
            self.log("添加证书失败: 日期格式无效")
            return False

        if issue_date >= expiry_date:
            self.log("添加证书失败: 过期日期必须晚于签发日期")
            return False
            
        # 如果提供了template_id，验证模板是否存在
        if template_id is not None:
            template = self.get_certificate_template(template_id)
            if not template:
                self.log(f"添加证书失败: 指定的证书模板(ID:{template_id})不存在")
                return False

        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if template_id is not None:
                cursor.execute("""
                    INSERT INTO certificates 
                    (serial_number, subject_name, public_key_fingerprint, issue_date, expiry_date, signature, template_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (serial_number, subject_name, public_key, issue_date, expiry_date, signature, template_id))
            else:
                cursor.execute("""
                    INSERT INTO certificates 
                    (serial_number, subject_name, public_key_fingerprint, issue_date, expiry_date, signature)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (serial_number, subject_name, public_key, issue_date, expiry_date, signature))
            conn.commit()
            self.log(f"证书添加成功: {serial_number} - {subject_name}")
            return True
        except mysql.connector.Error as err:
            self.log(f"添加证书失败: {err}")
            return False
        finally:
            cursor.close()
            conn.close()

    def revoke_certificate(self, serial_number):
        """撤销证书"""
        # 参数验证
        if not serial_number or len(serial_number) > 64:
            self.log("撤销证书失败: 无效的证书序列号")
            return False

        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 先检查证书是否存在且未被撤销
            cursor.execute("""
                SELECT status
                FROM certificates
                WHERE serial_number = %s
            """, (serial_number,))
            result = cursor.fetchone()

            if not result:
                self.log("撤销证书失败: 证书不存在")
                return False

            if result[0] == 'revoked':
                self.log("撤销证书失败: 证书已被撤销")
                return False

            cursor.execute("""
                UPDATE certificates
                SET status = 'revoked'
                WHERE serial_number = %s
            """, (serial_number,))
            conn.commit()
            return cursor.rowcount > 0
        except mysql.connector.Error as err:
            self.log(f"撤销证书失败: {err}")
            return False
        finally:
            cursor.close()
            conn.close()

    def verify_certificate(self, serial_number):
        """验证证书"""
        # 参数验证
        if not serial_number or len(serial_number) > 64:
            self.log("验证证书失败: 无效的证书序列号")
            return None

        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT serial_number, subject_name, status, issue_date, expiry_date
                FROM certificates
                WHERE serial_number = %s
            """, (serial_number,))
            cert = cursor.fetchone()

            if not cert:
                self.log("验证证书失败: 证书不存在")
                return None

            # 增加类型检查和时区转换
            from pytz import utc
            if not isinstance(cert['expiry_date'], datetime):
                raise ValueError("证书过期时间格式错误")

            # 统一使用UTC时区比较
            now_utc = datetime.now(utc)
            expiry_utc = cert['expiry_date'].astimezone(utc)

            if expiry_utc < now_utc:
                self.log("验证证书失败: 证书已过期")
                cert['status'] = 'expired'

            return cert
        except (mysql.connector.Error, ValueError, TypeError) as err:  # 增加异常类型
            self.log(f"验证证书失败: {err}")
            return None
        finally:
            cursor.close()
            conn.close()

    def close_connection(self, conn):
        """安全关闭连接，归还到连接池
        
        Args:
            conn: 数据库连接对象
        """
        try:
            if conn:
                conn.close()
        except Exception as e:
            self.log(f"关闭数据库连接时出错: {e}")

    def add_user(self, username, password_hash, role='user'):
        """添加用户"""
        # 参数验证
        if not username or not password_hash:
            self.log("添加用户失败: 用户名和密码不能为空")
            return False

        # 长度限制
        if len(username) > 64 or len(password_hash) > 128:
            self.log("添加用户失败: 用户名或密码哈希超出长度限制")
            return False

        # 角色验证
        valid_roles = ['admin', 'user']
        if role not in valid_roles:
            self.log("添加用户失败: 无效的用户角色")
            return False

        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 检查用户名是否已存在
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                self.log("添加用户失败: 用户名已存在")
                return False

            cursor.execute("""
                INSERT INTO users 
                (username, password_hash, role)
                VALUES (%s, %s, %s)
            """, (username, password_hash, role))
            conn.commit()
            return True
        except mysql.connector.Error as err:
            self.log(f"添加用户失败: {err}")
            return False
        finally:
            cursor.close()
            conn.close()

    def verify_user(self, username: str, password_hash: str) -> Optional[Dict]:
        """验证用户登录"""
        # 防御性编程：确保方法不会因任何原因崩溃
        try:
            # 参数验证 - 使用更安全的类型检查
            try:
                if not isinstance(username, str):
                    print("验证用户失败: 用户名必须是字符串类型")
                    return None
                if not isinstance(password_hash, str):
                    print("验证用户失败: 密码哈希必须是字符串类型")
                    return None
            except Exception as type_err:
                print(f"验证用户失败: 类型检查时出错 - {str(type_err)}")
                return None
                
            # 空值检查
            try:
                if not username or not password_hash:
                    print("验证用户失败: 用户名和密码不能为空")
                    return None
            except Exception as empty_err:
                print(f"验证用户失败: 空值检查时出错 - {str(empty_err)}")
                return None

            # 长度限制
            try:
                if len(username) > 64 or len(password_hash) > 128:
                    print("验证用户失败: 用户名或密码哈希超出长度限制")
                    return None
            except Exception as len_err:
                print(f"验证用户失败: 检查长度时出错 - {str(len_err)}")
                return None

            conn = None
            cursor = None
            try:
                # 安全获取数据库连接
                try:
                    # 确保连接池已初始化
                    if not hasattr(self, 'connection_pool') or self.connection_pool is None:
                        try:
                            with self._pool_lock:
                                if self.connection_pool is None:
                                    self._init_connection_pool()
                        except Exception as pool_err:
                            print(f"验证用户失败: 初始化连接池时出错 - {str(pool_err)}")
                            return None
                    
                    try:
                        conn = self.get_connection()
                    except Exception as get_conn_err:
                        print(f"验证用户失败: 获取连接时出错 - {str(get_conn_err)}")
                        return None
                        
                    if conn is None:
                        print("验证用户失败: 获取到的数据库连接为None")
                        return None
                        
                    if not hasattr(conn, 'cursor'):
                        print("验证用户失败: 数据库连接对象没有cursor方法")
                        return None
                except Exception as conn_err:
                    print(f"验证用户失败: 获取数据库连接时出错 - {str(conn_err)}")
                    return None
                    
                # 安全创建游标
                try:
                    cursor = conn.cursor(dictionary=True)  # 使用字典游标
                    if cursor is None:
                        print("验证用户失败: 创建的游标为None")
                        return None
                except Exception as cursor_err:
                    print(f"验证用户失败: 创建数据库游标时出错 - {str(cursor_err)}")
                    return None

                try:
                    print(f"正在验证用户: {username}")
                except Exception:
                    print("正在验证用户(无法显示用户名)")

                # 先检查用户是否存在
                try:
                    cursor.execute("""
                        SELECT id, username, password_hash, role 
                        FROM users 
                        WHERE username = %s
                    """, (username,))
                    user = cursor.fetchone()
                except Exception as query_err:
                    print(f"验证用户失败: 查询用户信息时出错 - {str(query_err)}")
                    return None

                if not user:
                    try:
                        print(f"用户 {username} 不存在")
                    except Exception:
                        print("用户不存在(无法显示用户名)")
                    return None

                # 验证密码 - 安全地访问字典键
                try:
                    if not isinstance(user, dict):
                        print(f"验证用户失败: 用户数据不是字典类型 - {type(user)}")
                        return None
                        
                    stored_hash = user.get('password_hash')
                    if stored_hash is None:
                        print("验证用户失败: 数据库中没有密码哈希值")
                        return None
                        
                    if stored_hash != password_hash:
                        try:
                            print(f"用户 {username} 密码验证失败")
                        except Exception:
                            print("密码验证失败(无法显示用户名)")
                        return None
                except Exception as pwd_err:
                    print(f"验证用户失败: 密码比对时出错 - {str(pwd_err)}")
                    return None

                # 安全地构建返回值
                try:
                    # 检查必要字段
                    user_id = user.get('id')
                    if user_id is None:
                        print("验证用户失败: 用户数据中缺少id字段")
                        return None
                        
                    user_name = user.get('username')
                    if user_name is None:
                        print("验证用户失败: 用户数据中缺少username字段")
                        return None
                    
                    # 角色可以有默认值
                    user_role = user.get('role', 'user')
                    
                    try:
                        print(f"用户 {username} 密码验证成功")
                    except Exception:
                        print("密码验证成功(无法显示用户名)")
                        
                    return {
                        'id': user_id,
                        'username': user_name,
                        'role': user_role
                    }
                except Exception as ret_err:
                    print(f"验证用户失败: 构建返回数据时出错 - {str(ret_err)}")
                    return None

            except mysql.connector.Error as err:
                print(f"验证用户失败: 数据库错误 - {str(err)}")
                return None
            except Exception as e:
                print(f"验证用户时发生未知错误: {str(e)}")
                return None
            finally:
                # 确保资源释放
                if cursor is not None:
                    try:
                        cursor.close()
                    except Exception as e:
                        print(f"关闭游标时出错: {str(e)}")
                if conn is not None:
                    try:
                        if hasattr(conn, 'is_connected') and callable(conn.is_connected):
                            try:
                                if conn.is_connected():
                                    conn.close()
                            except Exception as conn_check_err:
                                print(f"检查连接状态时出错: {str(conn_check_err)}")
                                # 尝试直接关闭
                                if hasattr(conn, 'close') and callable(conn.close):
                                    conn.close()
                        elif hasattr(conn, 'close') and callable(conn.close):
                            conn.close()
                    except Exception as e:
                        print(f"关闭连接时出错: {str(e)}")
        except Exception as outer_err:
            # 最外层异常捕获，确保方法永远不会抛出异常
            try:
                print(f"验证用户过程中发生严重错误: {str(outer_err)}")
            except:
                print("验证用户过程中发生严重错误且无法显示错误信息")
            return None

    def get_user_key_pairs(self, user_id: int) -> List[Dict]:
        """获取用户的所有密钥对
        
        Args:
            user_id: 用户ID
            
        Returns:
            密钥对列表，每个元素包含id, public_key_encrypted, public_key_fingerprint, created_at, status
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute("""
                    SELECT id, public_key_encrypted, public_key_fingerprint, created_at, status
                    FROM key_pairs
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                """, (user_id,))
                return cursor.fetchall()
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            self.log(f"获取用户密钥对失败: {str(e)}")
            return []

    def get_key_pair_by_fingerprint(self, fingerprint: str) -> Optional[Dict]:
        """通过指纹获取密钥对
        
        Args:
            fingerprint: 公钥指纹
            
        Returns:
            密钥对信息，失败返回None
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute("""
                    SELECT id, user_id, public_key_encrypted, public_key_fingerprint, created_at, status
                    FROM key_pairs
                    WHERE public_key_fingerprint = %s
                """, (fingerprint,))
                return cursor.fetchone()
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            self.log(f"通过指纹获取密钥对失败: {str(e)}")
            return None

    def add_key_pair(self, user_id: int, public_key_encrypted: str, fingerprint: str) -> bool:
        """添加密钥对
        
        Args:
            user_id: 用户ID
            public_key_encrypted: 加密后的公钥
            fingerprint: 公钥指纹
            
        Returns:
            成功返回True，失败返回False
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO key_pairs (user_id, public_key_encrypted, public_key_fingerprint, status)
                    VALUES (%s, %s, %s, 'active')
                """, (user_id, public_key_encrypted, fingerprint))
                conn.commit()
                return True
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            self.log(f"添加密钥对失败: {str(e)}")
            return False

    def get_certificates_by_fingerprint(self, fingerprint: str) -> List[Dict]:
        """通过公钥指纹获取证书列表
        
        Args:
            fingerprint: 公钥指纹
            
        Returns:
            证书列表
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute("""
                    SELECT id, serial_number, subject_name, status, issue_date, expiry_date, 
                           template_id, organization, department, email, usage, remarks, created_at
                    FROM certificates
                    WHERE public_key_fingerprint = %s
                    ORDER BY issue_date DESC
                """, (fingerprint,))
                return cursor.fetchall()
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            self.log(f"获取证书列表失败: {str(e)}")
            return []

    def update_user(self, user_id, password_hash=None, role=None):
        """更新用户信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            updates = []
            params = []
            if password_hash:
                updates.append("password_hash = %s")
                params.append(password_hash)
            if role:
                updates.append("role = %s")
                params.append(role)

            if not updates:
                return True

            params.append(user_id)
            cursor.execute(f"""
                UPDATE users
                SET {', '.join(updates)}
                WHERE id = %s
            """, tuple(params))
            conn.commit()
            return True
        except mysql.connector.Error as err:
            logging.error(f"更新用户失败: {err}")
            return False
        finally:
            cursor.close()
            conn.close()

    def delete_user(self, user_id):
        """删除用户"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                DELETE FROM users
                WHERE id = %s
            """, (user_id,))
            conn.commit()
            return True
        except mysql.connector.Error as err:
            logging.error(f"删除用户失败: {err}")
            return False
        finally:
            cursor.close()
            conn.close()

    def get_user(self, user_id):
        """获取用户信息"""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT id, username, role, created_at
                FROM users
                WHERE id = %s
            """, (user_id,))
            return cursor.fetchone()
        except mysql.connector.Error as err:
            logging.error(f"获取用户信息失败: {err}")
            return None
        finally:
            cursor.close()
            conn.close()

    def list_users(self):
        """列出所有用户"""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT id, username, role, created_at
                FROM users
            """)
            return cursor.fetchall()
        except mysql.connector.Error as err:
            logging.error(f"列出用户失败: {err}")
            return []
        finally:
            cursor.close()
            conn.close()

    def create_certificate_template(self, name, validity_period, key_usage, allowed_roles='admin,user'):
        """创建证书模板"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO certificate_templates 
                (name, validity_period, key_usage, allowed_roles)
                VALUES (%s, %s, %s, %s)
            """, (name, validity_period, key_usage, allowed_roles))
            conn.commit()
            return cursor.lastrowid
        except mysql.connector.Error as err:
            logging.error(f"创建证书模板失败: {err}")
            return None
        finally:
            cursor.close()
            conn.close()

    def update_certificate_template(self, template_id, name=None, validity_period=None, key_usage=None, allowed_roles=None):
        """更新证书模板"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            updates = []
            params = []
            if name:
                updates.append("name = %s")
                params.append(name)
            if validity_period:
                updates.append("validity_period = %s")
                params.append(validity_period)
            if key_usage:
                updates.append("key_usage = %s")
                params.append(key_usage)
            if allowed_roles:
                updates.append("allowed_roles = %s")
                params.append(allowed_roles)

            if not updates:
                return True

            params.append(template_id)
            cursor.execute(f"""
                UPDATE certificate_templates
                SET {', '.join(updates)}
                WHERE id = %s
            """, tuple(params))
            conn.commit()
            return True
        except mysql.connector.Error as err:
            logging.error(f"更新证书模板失败: {err}")
            return False
        finally:
            cursor.close()
            conn.close()

    def get_certificate_templates(self):
        """获取证书模板列表"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute("""
                    SELECT id, name, validity_period, key_usage, allowed_roles, created_at
                    FROM certificate_templates
                    ORDER BY created_at DESC
                """)
                templates = cursor.fetchall()
                
                if templates is None:
                    self.log("获取证书模板列表返回空结果")
                    return []
                    
                return templates
            except mysql.connector.Error as err:
                self.log(f"获取证书模板列表数据库错误: {err}")
                return []
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            self.log(f"获取证书模板列表失败: {e}")
            return []

    def get_certificate_template(self, template_id):
        """获取证书模板信息"""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT *
                FROM certificate_templates
                WHERE id = %s
            """, (template_id,))
            return cursor.fetchone()
        except mysql.connector.Error as err:
            logging.error(f"获取证书模板失败: {err}")
            return None
        finally:
            cursor.close()
            conn.close()

    def list_certificate_templates(self):
        """列出所有证书模板"""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT *
                FROM certificate_templates
            """)
            return cursor.fetchall()
        except mysql.connector.Error as err:
            logging.error(f"列出证书模板失败: {err}")
            return []
        finally:
            cursor.close()
            conn.close()

    def set_template_permission(self, template_id, user_id, can_use=True):
        """设置模板权限"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO template_permissions 
                (template_id, user_id, can_use)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE can_use = VALUES(can_use)
            """, (template_id, user_id, can_use))
            conn.commit()
            return True
        except mysql.connector.Error as err:
            logging.error(f"设置模板权限失败: {err}")
            return False
        finally:
            cursor.close()
            conn.close()

    def check_template_permission(self, template_id, user_id):
        """检查用户是否有权限使用模板"""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # 首先检查用户角色
            cursor.execute("SELECT role FROM users WHERE id = %s", (user_id,))
            user_result = cursor.fetchone()
            if not user_result:
                return False
            user_role = user_result['role']
            
            # 获取模板允许的角色
            cursor.execute("SELECT allowed_roles FROM certificate_templates WHERE id = %s", (template_id,))
            template_result = cursor.fetchone()
            if not template_result:
                return False
            allowed_roles = template_result['allowed_roles'].split(',')
            
            # 如果用户角色在允许的角色列表中，则有权限
            if user_role in allowed_roles:
                return True
                
            # 如果基于角色的权限检查失败，再检查具体的用户权限设置
            cursor.execute("""
                SELECT can_use
                FROM template_permissions
                WHERE template_id = %s AND user_id = %s
            """, (template_id, user_id))
            result = cursor.fetchone()
            return result['can_use'] if result else False
        except mysql.connector.Error as err:
            logging.error(f"检查模板权限失败: {err}")
            return False
        finally:
            cursor.close()
            conn.close()
            
    def delete_certificate_template(self, template_id):
        """删除证书模板"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 先删除与该模板相关的权限记录
            cursor.execute("""
                DELETE FROM template_permissions
                WHERE template_id = %s
            """, (template_id,))
            
            # 删除模板
            cursor.execute("""
                DELETE FROM certificate_templates
                WHERE id = %s
            """, (template_id,))
            
            conn.commit()
            return True
        except mysql.connector.Error as err:
            logging.error(f"删除证书模板失败: {err}")
            return False
        finally:
            cursor.close()
            conn.close()
            
    def get_certificate_applications(self):
        """获取证书申请列表"""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT serial_number, subject_name, organization, status, submit_date
                FROM certificate_applications
                WHERE status = 'pending'
                ORDER BY submit_date DESC
            """)
            return cursor.fetchall()
        except mysql.connector.Error as err:
            self.log(f"获取证书申请列表失败: {err}")
            return []
        finally:
            cursor.close()
            conn.close()