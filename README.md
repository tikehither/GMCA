# GMCA - 国密证书管理系统

基于SM2/SM3/SM4国密算法的完整证书管理系统，支持证书的全生命周期管理（申请、签发、审核、验证、吊销），采用C/S架构，支持本地部署和云服务器部署。

## 🚀 核心特性

- **国密算法支持**：全面采用SM2/SM3/SM4国密算法，符合中国国家密码标准（GM/T 0004-2012）
- **完整证书管理**：证书申请、审核、签发、查询、验证、吊销全流程支持
- **安全架构**：客户端-服务器分离架构，基于国密算法的安全通信
- **数据库集成**：MySQL数据库持久化存储，支持连接池
- **容器化部署**：Docker容器化部署，一键启动
- **图形界面**：友好的客户端GUI界面和服务器管理界面
- **云服务器支持**：支持云服务器部署，本地客户端连接

## 📁 项目结构

```
GMCA/
├── src/                               # 源代码目录
│   ├── server/                        # 服务器端代码
│   │   ├── server.py                  # 主服务器程序（异步TCP服务器）
│   │   ├── server_ui.py               # 服务器管理界面（PyQt5）
│   │   ├── start_server_ui.py         # 服务器UI启动器
│   │   ├── crypto_gmssl.py            # 国密算法实现（SM2/SM3/SM4）
│   │   ├── database.py                # 数据库操作核心（支持连接池）
│   │   ├── database_interface.py      # 数据库接口定义
│   │   ├── secure_logger.py           # 安全日志系统
│   │   ├── constants.py               # 常量定义
│   │   ├── requirements-server.txt    # 服务器依赖
│   │   └── keys/                      # 密钥存储目录（自动生成）
│   ├── client/                        # 客户端代码
│   │   ├── main_ui.py                 # 主用户界面
│   │   ├── login_ui.py                # 登录界面
│   │   ├── network.py                 # 网络通信模块（异步TCP客户端）
│   │   ├── crypto_gmssl.py            # 客户端加密模块
│   │   ├── start_client.py            # 客户端启动器
│   │   ├── requirements-client.txt    # 客户端依赖
│   │   └── README.md                  # 客户端说明
│   └── common/                        # 公共代码（预留）
├── config/                            # 配置文件目录
│   ├── database/                      # 数据库配置
│   │   ├── config.yaml                # 主配置文件
│   │   └── init.sql                   # 数据库初始化脚本
│   └── mysql/                         # MySQL配置
│       └── my.cnf                     # MySQL配置文件
├── deployments/                       # 部署配置
│   └── docker/                        # Docker部署
│       ├── docker-compose.yml         # Docker编排文件
│       ├── Dockerfile.server          # 服务器Dockerfile
│       ├── Dockerfile.client          # 客户端Dockerfile
│       ├── requirements-server.txt    # 服务器依赖
│       └── requirements-client.txt    # 客户端依赖
├── scripts/                           # 运维脚本
│   ├── start.sh                       # 启动脚本
│   ├── stop.sh                        # 停止脚本
│   └── restart.sh                     # 重启脚本
├── config/                            # 配置文件目录
│   └── database/                      # 数据库配置
│       ├── config.yaml                # 主配置文件
│       └── init.sql                   # 数据库初始化脚本
├── .gitignore                         # Git忽略文件
└── README.md                          # 项目说明文档
```

## 🛠️ 系统要求

### 环境要求
- **Python**: 3.8+
- **MySQL**: 8.0+
- **Docker**: 20.10+（可选，用于容器化部署）

### 依赖库
- **gmssl**: 国密算法实现（SM2/SM3/SM4）
- **mysql-connector-python**: MySQL数据库连接
- **PyQt5**: 图形界面框架
- **PyYAML**: YAML配置文件解析
- **asyncio**: 异步网络通信

## 🚀 快速开始

### 方式一：传统部署（推荐本地开发）

#### 1. 数据库初始化

```bash
# 启动MySQL服务
# Windows: 确保MySQL服务已启动
# Linux/Mac: sudo systemctl start mysql

# 初始化数据库
mysql -u root -p < config/database/init.sql
# 或手动执行SQL文件
```

#### 2. 启动CA服务器

```bash
# 安装服务器依赖
pip install -r src/server/requirements-server.txt

# 启动服务器（无UI）
python src/server/server.py

# 或启动带UI的服务器
python src/server/start_server_ui.py
```

服务器启动后会：
- 自动初始化数据库表结构
- 生成SM2/SM4密钥对
- 生成CA根证书
- 监听 `0.0.0.0:8888` 端口

#### 3. 启动客户端

```bash
# 安装客户端依赖
pip install -r src/client/requirements-client.txt

# 启动客户端
python src/client/start_client.py
```

### 方式二：Docker容器化部署（推荐生产环境）

```bash
# 进入Docker目录
cd deployments/docker

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f server
```

### 方式三：云服务器部署（推荐远程使用）

#### 1. 云服务器端配置

```bash
# 1. 在云服务器上安装依赖
pip install -r src/server/requirements-server.txt

# 2. 配置MySQL
# 确保MySQL监听 0.0.0.0:3306
# 授权远程访问
mysql -u root -p
GRANT ALL PRIVILEGES ON CA.* TO 'root'@'%' IDENTIFIED BY 'your_password';
FLUSH PRIVILEGES;

# 3. 启动服务器
python src/server/start_server_ui.py

# 4. 配置防火墙
# 开放 8888 端口
```

#### 2. 本地客户端配置

**方法一：使用环境变量**

```bash
# Windows PowerShell
$env:SERVER_HOST="云服务器公网IP"
$env:SERVER_PORT="8888"
python src/client/start_client.py

# Windows CMD
set SERVER_HOST=云服务器公网IP
set SERVER_PORT=8888
python src/client/start_client.py
```

**方法二：修改启动脚本**

编辑 `src/client/start_client.py` 第17行：
```python
server_host = os.environ.get('SERVER_HOST', '云服务器公网IP')
```

**方法三：修改网络模块**

编辑 `src/client/network.py` 第10行：
```python
def __init__(self, host='云服务器公网IP', port=8888):
```

## 📦 依赖说明

### 服务器端依赖 (`src/server/requirements-server.txt`)

```
gmssl>=3.1.0
mysql-connector-python>=8.0.0
PyYAML>=6.0
PyQt5>=5.15.0
asyncio
```

主要功能：
- **gmssl**: 国密算法实现（SM2/SM3/SM4）
- **mysql-connector-python**: MySQL数据库连接池
- **PyYAML**: YAML配置文件解析
- **PyQt5**: 服务器管理界面
- **asyncio**: 异步TCP服务器

### 客户端依赖 (`src/client/requirements-client.txt`)

```
gmssl>=3.1.0
PyQt5>=5.15.0
asyncio
```

主要功能：
- **gmssl**: 国密算法实现（SM2/SM3/SM4）
- **PyQt5**: 图形界面框架
- **asyncio**: 异步网络通信

## 🔐 国密算法集成

### 算法特点

| 算法 | 用途 | 特点 |
|------|------|------|
| **SM2** | 证书签名、密钥交换 | 椭圆曲线公钥算法，256位密钥 |
| **SM3** | 数据哈希、密码存储 | 国密哈希算法，256位哈希值 |
| **SM4** | 数据加密 | 分组密码，128位密钥 |

### 实现位置

- **服务器端**: `src/server/crypto_gmssl.py`
  - `GMSCrypto` 类：完整的国密算法实现
  - `sm2_encrypt/decrypt`: SM2加密/解密
  - `sm3_hash`: SM3哈希
  - `sm4_encrypt/decrypt`: SM4加密/解密
  - `generate_root_certificate`: 生成CA根证书

- **客户端**: `src/client/crypto_gmssl.py`
  - `ClientGMSCrypto` 类：客户端国密算法实现
  - `load_or_generate_sm2_key_pair`: 生成SM2密钥对
  - `sm3_hash`: SM3哈希
  - `sm4_encrypt/decrypt`: SM4加密/解密

### 主要应用

1. **密码哈希**：用户登录密码使用SM3哈希存储
2. **证书签名**：CA使用SM2私钥对证书进行签名
3. **数据加密**：SM4用于敏感数据加密
4. **密钥交换**：SM2用于密钥协商

## 📊 系统功能

### 证书管理

| 功能 | 描述 | 状态 |
|------|------|------|
| **证书申请** | 用户提交证书申请，包含公钥和个人信息 | ✅ |
| **证书审核** | 管理员审核证书申请，决定签发或拒绝 | ✅ |
| **证书签发** | CA使用私钥对证书进行签名并签发 | ✅ |
| **证书查询** | 用户查询自己的证书状态和信息 | ✅ |
| **证书验证** | 验证证书的有效性和签名 | ✅ |
| **证书吊销** | 吊销无效或泄露的证书 | ✅ |
| **证书模板** | 预定义证书模板，简化申请流程 | ✅ |

### 用户管理

| 功能 | 描述 | 角色 |
|------|------|------|
| **用户注册** | 新用户注册账号 | 所有用户 |
| **用户登录** | 使用SM3密码哈希登录 | 所有用户 |
| **密码修改** | 修改用户密码 | 所有用户 |
| **权限管理** | 基于角色的访问控制 | 管理员 |
| **角色定义** | admin（管理员）、auditor（审计员）、user（普通用户） | - |

### 安全管理

| 功能 | 描述 |
|------|------|
| **安全日志** | 记录所有关键操作，支持审计追踪 |
| **操作审计** | 记录用户操作，包括时间、IP、操作类型 |
| **数据加密** | 敏感数据使用SM4加密存储 |
| **密钥管理** | 自动管理SM2/SM4密钥，支持密钥轮换 |

## ⚙️ 配置说明

### 主配置文件 (`config/database/config.yaml`)

```yaml
# 服务器配置
server:
  host: 0.0.0.0          # 监听地址（0.0.0.0表示所有接口）
  port: 8888             # 监听端口
  max_connections: 100   # 最大连接数

# 数据库配置
database:
  type: mysql
  host: localhost        # 数据库主机
  port: 3306             # 数据库端口
  database: CA           # 数据库名
  user: root             # 数据库用户
  password: your_password # 数据库密码
  pool_size: 5           # 连接池大小
  connect_timeout: 30    # 连接超时（秒）
  retry_count: 5         # 重试次数
  retry_delay: 3         # 重试延迟（秒）

# 安全配置
security:
  key_size: 2048         # 密钥长度
  cert_validity_days: 365 # 证书有效期（天）
  session_timeout: 3600  # 会话超时（秒）
  max_failed_attempts: 5 # 最大失败尝试次数
  lockout_duration: 300  # 锁定时长（秒）

# 日志配置
logging:
  level: INFO            # 日志级别（DEBUG/INFO/WARNING/ERROR）
  file: server.log       # 日志文件
  max_size: 10485760     # 日志文件最大大小（字节）
  backup_count: 5        # 保留的备份日志文件数

# 安全日志配置
secure_logging:
  enabled: true
  encrypt_sensitive_fields: true
  hash_verification: true
  audit_role: 'auditor'
  log_dir: 'logs'
  log_files:
    certificate: 'certificate_log.json'
    admin: 'admin_log.json'
    audit: 'audit_log.json'
    secure: 'secure_log.json'
  sensitive_fields:
    certificate: ['subject_key', 'issuer_key']
    admin: ['ip_address', 'session_key', 'password']
```

### 环境变量

| 变量名 | 说明 | 默认值 | 示例 |
|--------|------|--------|------|
| `SERVER_HOST` | 服务器地址 | 127.0.0.1 | 192.168.1.100 |
| `SERVER_PORT` | 服务器端口 | 8888 | 8888 |

## 🔧 开发指南

### 代码结构说明

#### 服务器端模块

| 模块 | 功能 | 主要类/函数 |
|------|------|-------------|
| `server.py` | 异步TCP服务器 | `CAServer` |
| `server_ui.py` | 服务器管理界面 | `CAServerUI` |
| `crypto_gmssl.py` | 国密算法实现 | `GMSCrypto` |
| `database.py` | 数据库操作 | `DatabaseManager` |
| `secure_logger.py` | 安全日志系统 | `SecureLoggerManager` |

#### 客户端模块

| 模块 | 功能 | 主要类/函数 |
|------|------|-------------|
| `main_ui.py` | 主用户界面 | `CAClient` |
| `login_ui.py` | 登录界面 | `LoginDialog` |
| `network.py` | 网络通信 | `AsyncClient` |
| `crypto_gmssl.py` | 客户端加密 | `ClientGMSCrypto` |

### 添加新功能

1. **添加服务器端功能**
   - 在 `server.py` 中添加新的action处理
   - 在 `database.py` 中添加数据库操作
   - 在 `crypto_gmssl.py` 中添加加密逻辑

2. **添加客户端功能**
   - 在 `main_ui.py` 中添加UI界面
   - 在 `network.py` 中添加网络请求
   - 在 `crypto_gmssl.py` 中添加加密逻辑

3. **扩展数据库**
   - 修改 `config/database/init.sql`
   - 在 `database.py` 中添加新的数据库操作

### 调试技巧

```bash
# 启用详细日志
# 修改 config/database/config.yaml 中的 logging.level 为 DEBUG

# 查看服务器日志
tail -f logs/server.log

# 查看安全日志
cat logs/secure_log.json

# 测试数据库连接
python src/server/database.py

# 测试国密算法
python src/server/crypto_gmssl.py
```

## 🐛 故障排除

### 常见问题

#### 1. 数据库连接失败

**问题**: `Access denied for user 'root'@'localhost'`

**解决方案**:
```bash
# 检查MySQL服务状态
# Windows: services.msc -> MySQL
# Linux: sudo systemctl status mysql

# 验证数据库配置
# 检查 config/database/config.yaml 中的连接参数

# 授权远程访问
mysql -u root -p
GRANT ALL PRIVILEGES ON CA.* TO 'root'@'%' IDENTIFIED BY 'your_password';
FLUSH PRIVILEGES;
```

#### 2. 服务器启动失败

**问题**: `Address already in use`

**解决方案**:
```bash
# Windows
netstat -ano | findstr :8888
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8888
kill -9 <PID>
```

#### 3. 客户端无法连接服务器

**问题**: `无法连接到服务器`

**解决方案**:
```bash
# 检查服务器是否运行
netstat -an | grep 8888

# 检查防火墙设置
# Windows: 防火墙 -> 允许应用通过防火墙
# Linux: sudo ufw allow 8888

# 测试网络连通性
telnet <server_ip> 8888
```

#### 4. 国密算法错误

**问题**: `gmssl library not found`

**解决方案**:
```bash
# 安装gmssl库
pip install gmssl

# 或使用国内镜像
pip install gmssl -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 日志查看

```bash
# 服务器日志
cat logs/server.log

# 安全日志
cat logs/secure_log.json

# 数据库日志
# Docker: docker logs <container_name>
# 本地: 查看MySQL日志文件
```

## 📈 性能优化

### 数据库优化

```yaml
# 在 config/database/config.yaml 中调整
database:
  pool_size: 10          # 增加连接池大小
  connect_timeout: 60    # 增加连接超时
  retry_count: 10        # 增加重试次数
```

### 服务器优化

- 启用连接池：`pool_size` 设置为 10-20
- 优化查询：使用索引
- 定期清理：清理过期证书和日志

## 🔒 安全建议

### 生产环境部署

1. **修改默认密码**
   - 数据库密码
   - 默认用户密码（admin/user）

2. **启用SSL/TLS**
   - 配置HTTPS
   - 使用证书加密通信

3. **配置防火墙**
   - 只开放必要端口
   - 限制IP访问

4. **定期安全审计**
   - 查看安全日志
   - 审计用户操作

### 密钥管理

1. **保护私钥文件**
   - 设置文件权限
   - 定期备份
   - 使用密钥加密

2. **定期更换密钥**
   - SM2密钥：每年更换
   - SM4密钥：每季度更换

3. **使用HSM**
   - 硬件安全模块
   - 保护密钥不被泄露

## 📦 部署示例

### Docker Compose部署

```yaml
# deployments/docker/docker-compose.yml
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    container_name: ca-mysql
    environment:
      MYSQL_ROOT_PASSWORD: rootpassword
      MYSQL_DATABASE: CA
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
      - ./config/database/init.sql:/docker-entrypoint-initdb.d/init.sql

  server:
    build:
      context: .
      dockerfile: deployments/docker/Dockerfile.server
    container_name: ca-server
    ports:
      - "8888:8888"
    depends_on:
      - mysql
    volumes:
      - ./logs:/app/logs

  client:
    build:
      context: .
      dockerfile: deployments/docker/Dockerfile.client
    container_name: ca-client
    depends_on:
      - server
    environment:
      - SERVER_HOST=server
      - SERVER_PORT=8888

volumes:
  mysql_data:
```

### 云服务器部署

```bash
# 1. 启动云服务器
# 2. 安装依赖
pip install -r src/server/requirements-server.txt

# 3. 配置MySQL
mysql -u root -p
GRANT ALL PRIVILEGES ON CA.* TO 'root'@'%' IDENTIFIED BY 'your_password';
FLUSH PRIVILEGES;

# 4. 启动服务器
python src/server/start_server_ui.py

# 5. 配置防火墙
# 开放 8888 端口
```

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进项目：

1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

### 贡献类型

- **Bug修复**: 修复已知问题
- **新功能**: 添加新功能
- **文档改进**: 改进文档
- **代码优化**: 优化代码结构

## 📄 许可证

本项目基于原有代码构建，请遵循原有许可证。

## 📞 支持与联系

如有问题或建议，请：

1. 查看项目文档和FAQ
2. 提交GitHub Issue
3. 联系项目维护者

## 📚 相关资源

- [国密算法标准 GM/T 0004-2012](https://www.gmbz.org.cn/)
- [gmssl库文档](https://github.com/duanhongyi/gmssl)
- [MySQL官方文档](https://dev.mysql.com/doc/)

---

**GMCA - 安全、可靠、符合国标的证书管理系统** 🛡️
