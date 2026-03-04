-- CA 数据库初始化脚本
-- 创建数据库和用户

-- 确保使用正确的数据库
USE CA;

-- 创建证书模板表
CREATE TABLE IF NOT EXISTS certificate_templates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    validity_period INT NOT NULL,
    key_usage VARCHAR(255) NOT NULL,
    allowed_roles VARCHAR(50) DEFAULT 'admin,user',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    role ENUM('admin', 'user') DEFAULT 'user',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建证书表
CREATE TABLE IF NOT EXISTS certificates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    serial_number VARCHAR(64) UNIQUE NOT NULL,
    subject_name VARCHAR(255) NOT NULL,
    public_key TEXT NOT NULL,
    status ENUM('pending', 'valid', 'revoked', 'rejected') DEFAULT 'pending',
    issue_date DATETIME NOT NULL,
    expiry_date DATETIME NOT NULL,
    signature TEXT NOT NULL,
    template_id INT,
    organization VARCHAR(255),
    department VARCHAR(255),
    email VARCHAR(255),
    usage VARCHAR(255),
    remarks TEXT,
    FOREIGN KEY (template_id) REFERENCES certificate_templates(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建模板权限表
CREATE TABLE IF NOT EXISTS template_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    template_id INT NOT NULL,
    user_id INT NOT NULL,
    can_use BOOLEAN DEFAULT true,
    FOREIGN KEY (template_id) REFERENCES certificate_templates(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE KEY unique_template_user (template_id, user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;