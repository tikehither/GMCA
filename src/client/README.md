# Python CA System

基于Python的CA（证书颁发机构）系统，采用C/S架构，使用国密算法实现。

## 功能特点

- 基于国密算法的证书管理系统
- 采用SM2进行证书签名
- 使用SM4进行网络通信加密
- 使用SM3进行数据哈希
- 支持证书的申请、签发、验证和撤销
- 图形化客户端界面

## 系统要求

- Python 3.8+
- 其他依赖项请参考requirements.txt

## 项目结构

```
ca/
├── client/         # 客户端代码
├── server/         # 服务端代码
├── requirements.txt # 项目依赖
└── README.md       # 项目说明
```

## 安装说明

1. 克隆项目到本地
2. 安装依赖：`pip install -r requirements.txt`

## 使用说明

### 服务端

1. 进入server目录
2. 运行 `python server.py`

### 客户端

1. 进入client目录
2. 运行 `python client.py`