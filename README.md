# GMCA_CA - 国密证书管理系统

基于SM3国密算法的完整证书管理系统，支持证书的全生命周期管理（申请、签发、验证、吊销）。

## 🚀 核心特性

- **国密算法支持**：全面采用SM3国密哈希算法，符合中国国家密码标准
- **完整证书管理**：证书申请、签发、验证、吊销全流程支持
- **安全架构**：客户端-服务器分离架构，安全通信机制
- **数据库集成**：MySQL数据库持久化存储
- **容器化部署**：Docker容器化，一键部署
- **图形界面**：友好的客户端GUI界面

## 📁 项目结构

```
GMCA_CA/
├── README.md                          # 项目说明文档
├── src/                               # 源代码目录
│   ├── server/                        # 服务器端代码
│   │   ├── server.py                  # 主服务器程序
│   │   ├── server_ui.py               # 服务器管理界面
│   │   ├── crypto_fixed.py            # SM3国密算法实现
│   │   ├── database.py                # 数据库操作核心
│   │   ├── database_interface.py      # 数据库接口
│   │   ├── secure_logger.py           # 安全日志系统
│   │   ├── init_db.py                 # 数据库初始化
│   │   ├── start_server_ui.py         # 服务器UI启动器
│   │   └── constants.py               # 常量定义
│   ├── client/                        # 客户端代码
│   │   ├── CAGM.py                    # 客户端主程序
│   │   ├── main_ui.py                 # 主用户界面
│   │   ├── login_ui.py                # 登录界面
│   │   ├── crypto_fixed.py            # 客户端加密模块
│   │   ├── network.py                 # 网络通信模块
│   │   ├── start_client.py            # 客户端启动器
│   │   ├── standard_start.py          # 标准启动脚本
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
├── tests/                             # 测试目录（预留）
│   ├── unit/                          # 单元测试
│   └── integration/                   # 集成测试
└── .gitignore                         # Git忽略文件
```

## 🛠️ 快速开始

### 环境要求
- Python 3.9+
- MySQL 8.0+
- Docker & Docker Compose（可选）

### 1. 传统部署方式

#### 数据库初始化
```bash
# 启动MySQL服务
docker run -d --name ca-mysql \
  -p 3307:3306 \
  -e MYSQL_ROOT_PASSWORD=rootpassword \
  -e MYSQL_DATABASE=CA \
  mysql:8.0

# 初始化数据库
python src/server/database.py
```

#### 启动CA服务器
```bash
# 安装服务器依赖
pip install -r deployments/docker/requirements-server.txt

# 启动服务器
python src/server/server.py
# 或启动带UI的服务器
python src/server/start_server_ui.py
```

#### 启动客户端
```bash
# 安装客户端依赖
pip install -r deployments/docker/requirements-client.txt

# 启动客户端
python src/client/start_client.py
```

### 2. Docker容器化部署（推荐）

```bash
# 使用Docker Compose一键部署
cd deployments/docker
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f server
```

## 📦 依赖说明

### 服务器端依赖
服务器端需要以下依赖:
```bash
pip install -r deployments/docker/requirements-server.txt
```

主要依赖:
- **mysql-connector-python**: MySQL数据库连接
- **gmssl**: 国密算法(SM2/SM3/SM4)实现
- **PyYAML**: YAML配置文件解析
- **asyncio**: 异步网络通信
- **cryptography**: 加密算法支持
- **PyQt5**: 服务器UI界面(可选)

### 客户端依赖
客户端需要以下依赖:
```bash
pip install -r deployments/docker/requirements-client.txt
```

主要依赖:
- **PyQt5**: 图形界面框架
- **gmssl**: 国密算法(SM2/SM3/SM4)实现
- **cryptography**: 加密算法支持
- **asyncio**: 异步网络通信

## 🔐 SM3国密算法集成

本项目已全面集成SM3国密哈希算法：

### 算法特点
- **国家标准**：符合GM/T 0004-2012标准
- **安全性**：256位哈希值，抗碰撞性强
- **兼容性**：保持与SHA256相同的接口和输出格式

### 实现位置
- `src/server/crypto_fixed.py` - 服务器端SM3实现
- `src/client/crypto_fixed.py` - 客户端SM3实现

### 主要应用
1. **密码哈希**：用户登录密码使用SM3哈希存储
2. **数据完整性**：证书和关键数据完整性验证
3. **数字签名**：支持基于SM3的数字签名

## 📊 系统功能

### 证书管理
- ✅ 证书申请与提交
- ✅ 证书审核与签发
- ✅ 证书查询与验证
- ✅ 证书吊销与更新
- ✅ 证书模板管理

### 用户管理
- ✅ 多角色用户系统（管理员、审计员、普通用户）
- ✅ 基于SM3的安全密码存储
- ✅ 权限控制和访问管理

### 安全管理
- ✅ 安全日志记录
- ✅ 操作审计追踪
- ✅ 数据加密传输
- ✅ 防篡改机制

## ⚙️ 配置说明

### 主配置文件 (`config/database/config.yaml`)
```yaml
database:
  host: localhost
  port: 3307
  user: root
  password: rootpassword
  name: CA

server:
  host: 0.0.0.0
  port: 8888
  debug: false

security:
  hash_algorithm: sm3  # 使用SM3国密算法
  session_timeout: 3600
```

### 数据库配置
- **数据库名**: CA
- **默认端口**: 3307（避免与系统MySQL冲突）
- **默认用户**: root / rootpassword

## 🔧 开发指南

### 代码结构说明
- **服务器端**：采用模块化设计，各功能分离
- **客户端**：GUI界面与业务逻辑分离
- **配置管理**：集中式配置管理
- **安全模块**：独立的加密和安全组件

### 扩展开发
1. **添加新功能模块**：在相应目录创建新模块
2. **修改算法实现**：更新`crypto_fixed.py`文件
3. **添加新配置**：在`config.yaml`中添加配置项
4. **扩展数据库**：修改`init.sql`和`database.py`

## 🐛 故障排除

### 常见问题
1. **数据库连接失败**
   - 检查MySQL服务状态
   - 验证配置文件中的连接参数
   - 检查防火墙设置

2. **SM3算法问题**
   - 确保`gmssl`库正确安装
   - 检查算法实现代码

3. **客户端连接失败**
   - 验证服务器地址和端口
   - 检查网络连通性
   - 查看服务器日志

### 日志查看
```bash
# 查看服务器日志
tail -f logs/server.log

# 查看数据库日志
docker logs ca-mysql

# 查看安全日志
cat logs/secure_log.json
```

## 📈 性能优化

### 数据库优化
- 使用索引优化查询性能
- 定期清理历史数据
- 配置连接池

### 服务器优化
- 启用缓存机制
- 优化证书验证算法
- 使用异步处理

## 🔒 安全建议

1. **生产环境部署**
   - 修改所有默认密码
   - 启用SSL/TLS加密
   - 配置防火墙规则
   - 定期安全审计

2. **密钥管理**
   - 保护私钥文件
   - 定期更换密钥
   - 使用硬件安全模块（HSM）

3. **访问控制**
   - 实施最小权限原则
   - 启用多因素认证
   - 记录所有操作日志

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进项目：

1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 许可证

本项目基于原有代码构建，请遵循原有许可证。

## 📞 支持与联系

如有问题或建议，请：
1. 查看项目文档和FAQ
2. 提交GitHub Issue
3. 联系项目维护者

---

**GMCA_CA - 安全、可靠、符合国标的证书管理系统** 🛡️