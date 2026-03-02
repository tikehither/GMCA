import mysql.connector
import logging
import yaml
import time

class DatabaseInitializer:
    def __init__(self, log_callback=None):
        self.max_retries = 3
        self.retry_delay = 2
        self.log_callback = log_callback or (lambda x: None)
        self.config = self._load_config()

    def log(self, message):
        """统一的日志处理"""
        if self.log_callback:
            self.log_callback(message)
        logging.info(message)

    def _load_config(self):
        """加载数据库配置"""
        try:
            self.log("开始读取数据库配置")
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            db_config = config.get('database', {})
            config_dict = {
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
            missing_fields = [field for field in required_fields if not config_dict.get(field)]
            if missing_fields:
                raise ValueError(f"缺少必要的数据库配置项: {', '.join(missing_fields)}")

            self.log(f"数据库配置已加载: {config_dict['host']}:{config_dict['port']}")
            return config_dict

        except Exception as e:
            self.log(f"加载数据库配置失败: {str(e)}")
            raise

    def init_database_with_retry(self):
        """带重试机制的数据库初始化"""
        for attempt in range(self.max_retries):
            try:
                self.log(f"尝试初始化数据库 (尝试 {attempt + 1}/{self.max_retries})")
                self.init_database()
                self.log("数据库初始化成功")
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

            # 先不指定数据库名称连接MySQL服务器
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

            # 检查数据库是否存在
            cursor.execute(f"SHOW DATABASES LIKE '{self.config['database']}'")
            database_exists = cursor.fetchone() is not None

            if not database_exists:
                self.log(f"尝试创建数据库 {self.config['database']}")
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.config['database']}")
            else:
                self.log(f"数据库 {self.config['database']} 已存在")

            cursor.execute(f"USE {self.config['database']}")
            self.log(f"成功切换到数据库 {self.config['database']}")

            # 检查并创建证书模板表
            self._create_certificate_templates_table(cursor)

            # 检查并创建用户表
            self._create_users_table(cursor)

            # 检查并创建证书申请表
            self._create_certificate_applications_table(cursor)

            # 检查并创建证书表
            self._create_certificates_table(cursor)

            # 检查并创建模板权限表
            self._create_template_permissions_table(cursor)
            
            # 检查并创建会话表
            self._create_sessions_table(cursor)

            # 添加默认用户
            self._add_default_users(cursor)

            conn.commit()
            self.log("数据库初始化完成")

        except Exception as e:
            self.log(f"数据库操作失败: {str(e)}")
            if conn and conn.is_connected():
                conn.rollback()
            raise

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    def _check_and_update_table_structure(self, cursor, table_name, expected_columns):
        """检查并更新表结构"""
        # 获取当前表结构
        cursor.execute(f"SHOW COLUMNS FROM {table_name}")
        current_columns = {row[0]: row[1:] for row in cursor.fetchall()}
        
        # 检查缺失的列
        for col_name, col_def in expected_columns.items():
            if col_name not in current_columns:
                self.log(f"添加缺失的列 {col_name} 到 {table_name} 表")
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}")
        
        # 检查多余的列
        for col_name in current_columns:
            if col_name not in expected_columns:
                # 检查列是否有数据
                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {col_name} IS NOT NULL")
                count = cursor.fetchone()[0]
                if count == 0:
                    self.log(f"删除无用的列 {col_name} 从 {table_name} 表")
                    cursor.execute(f"ALTER TABLE {table_name} DROP COLUMN {col_name}")
                else:
                    self.log(f"列 {col_name} 包含数据，保留")

    def _create_certificate_templates_table(self, cursor):
        """创建证书模板表"""
        cursor.execute("SHOW TABLES LIKE 'certificate_templates'")
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS certificate_templates (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    validity_period INT NOT NULL,
                    key_usage VARCHAR(255) NOT NULL,
                    allowed_roles VARCHAR(50) DEFAULT 'admin,user',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            self.log("创建证书模板表成功")
        else:
            expected_columns = {
                'id': 'INT AUTO_INCREMENT PRIMARY KEY',
                'name': 'VARCHAR(255) NOT NULL',
                'validity_period': 'INT NOT NULL',
                'key_usage': 'VARCHAR(255) NOT NULL',
                'allowed_roles': "VARCHAR(50) DEFAULT 'admin,user'",
                'created_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
                'updated_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'
            }
            self._check_and_update_table_structure(cursor, 'certificate_templates', expected_columns)

    def _create_users_table(self, cursor):
        """创建用户表"""
        cursor.execute("SHOW TABLES LIKE 'users'")
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(64) UNIQUE NOT NULL,
                    password_hash VARCHAR(128) NOT NULL,
                    role ENUM('admin', 'user') DEFAULT 'user',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.log("创建用户表成功")
        else:
            expected_columns = {
                'id': 'INT AUTO_INCREMENT PRIMARY KEY',
                'username': 'VARCHAR(64) UNIQUE NOT NULL',
                'password_hash': 'VARCHAR(128) NOT NULL',
                'role': "ENUM('admin', 'user') DEFAULT 'user'",
                'created_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP'
            }
            self._check_and_update_table_structure(cursor, 'users', expected_columns)

    def _create_certificate_applications_table(self, cursor):
        """创建证书申请表"""
        cursor.execute("SHOW TABLES LIKE 'certificate_applications'")
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS certificate_applications (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    serial_number VARCHAR(64) UNIQUE NOT NULL,
                    subject_name VARCHAR(255) NOT NULL,
                    public_key TEXT NOT NULL,
                    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
                    submit_date DATETIME NOT NULL,
                    template_id INT NOT NULL,
                    user_id INT,
                    organization VARCHAR(255),
                    department VARCHAR(255),
                    email VARCHAR(255),
                    `usage` VARCHAR(255),
                    remarks TEXT,
                    FOREIGN KEY (template_id) REFERENCES certificate_templates(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            self.log("创建证书申请表成功")

    def _create_certificates_table(self, cursor):
        """创建证书表"""
        cursor.execute("SHOW TABLES LIKE 'certificates'")
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS certificates (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    serial_number VARCHAR(64) UNIQUE NOT NULL,
                    subject_name VARCHAR(255) NOT NULL,
                    public_key TEXT NOT NULL,
                    user_info TEXT,
                    status ENUM('valid', 'revoked', 'pending') DEFAULT 'valid',
                    issue_date DATETIME NOT NULL,
                    expiry_date DATETIME NOT NULL,
                    usage_purpose VARCHAR(255),
                    cert_hash VARCHAR(128),
                    signature TEXT,
                    template_id INT,
                    organization VARCHAR(255),
                    department VARCHAR(255),
                    email VARCHAR(255),
                    FOREIGN KEY (template_id) REFERENCES certificate_templates(id)
                )
            """)
            self.log("创建证书表成功")
        else:
            expected_columns = {
                'id': 'INT AUTO_INCREMENT PRIMARY KEY',
                'serial_number': 'VARCHAR(64) UNIQUE NOT NULL',
                'subject_name': 'VARCHAR(255) NOT NULL',
                'public_key': 'TEXT NOT NULL',
                'user_info': 'TEXT',
                'status': "ENUM('valid', 'revoked', 'pending') DEFAULT 'valid'",
                'issue_date': 'DATETIME NOT NULL',
                'expiry_date': 'DATETIME NOT NULL',
                'usage_purpose': 'VARCHAR(255)',
                'cert_hash': 'VARCHAR(128)',
                'signature': 'TEXT',
                'template_id': 'INT',
                'organization': 'VARCHAR(255)',
                'department': 'VARCHAR(255)',
                'email': 'VARCHAR(255)'
            }
            self._check_and_update_table_structure(cursor, 'certificates', expected_columns)

    def _create_template_permissions_table(self, cursor):
        """创建模板权限表"""
        cursor.execute("SHOW TABLES LIKE 'template_permissions'")
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS template_permissions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    template_id INT NOT NULL,
                    user_id INT NOT NULL,
                    can_use BOOLEAN DEFAULT true,
                    FOREIGN KEY (template_id) REFERENCES certificate_templates(id),
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE KEY unique_template_user (template_id, user_id)
                )
            """)
            self.log("创建模板权限表成功")
            
    def _create_sessions_table(self, cursor):
        """创建会话表"""
        cursor.execute("SHOW TABLES LIKE 'sessions'")
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    session_key TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    expires_at DATETIME NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE KEY unique_user_session (user_id)
                )
            """)
            self.log("创建会话表成功")

    def _add_default_users(self, cursor):
        """添加默认用户"""
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]

        if user_count == 0:
            cursor.execute("""
                INSERT INTO users (username, password_hash, role)
                VALUES ('admin', 'e86f78a8a3caf0b60d8e74e5942aa6d86dc150cd3c03338aef25b7d2d7e3acc7', 'admin'),
                       ('user', 'e86f78a8a3caf0b60d8e74e5942aa6d86dc150cd3c03338aef25b7d2d7e3acc7', 'user')
            """)
            self.log("添加默认用户成功")
        else:
            self.log("用户表已存在数据，跳过添加默认用户")

def main():
    logging.basicConfig(level=logging.INFO)
    initializer = DatabaseInitializer()
    try:
        initializer.init_database_with_retry()
        print("数据库初始化成功完成！")
    except Exception as e:
        print(f"数据库初始化失败: {str(e)}")

if __name__ == '__main__':
    main()