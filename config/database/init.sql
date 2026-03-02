-- CA 数据库初始化脚本
-- 创建数据库和用户

-- 确保使用正确的数据库
USE CA;

-- 创建证书表
CREATE TABLE IF NOT EXISTS certificates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    serial_number VARCHAR(64) NOT NULL UNIQUE,
    subject_name VARCHAR(255) NOT NULL,
    issuer_name VARCHAR(255) NOT NULL,
    public_key TEXT NOT NULL,
    private_key_encrypted TEXT,
    validity_start DATETIME NOT NULL,
    validity_end DATETIME NOT NULL,
    status ENUM('active', 'revoked', 'expired') DEFAULT 'active',
    revocation_reason TEXT,
    revocation_date DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_serial_number (serial_number),
    INDEX idx_status (status),
    INDEX idx_validity_end (validity_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    role ENUM('admin', 'user', 'auditor') DEFAULT 'user',
    failed_attempts INT DEFAULT 0,
    locked_until DATETIME,
    last_login DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建操作日志表
CREATE TABLE IF NOT EXISTS operation_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    operation_type VARCHAR(50) NOT NULL,
    operation_details TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    status ENUM('success', 'failure') DEFAULT 'success',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_operation_type (operation_type),
    INDEX idx_created_at (created_at),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建证书请求表
CREATE TABLE IF NOT EXISTS certificate_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id VARCHAR(64) NOT NULL UNIQUE,
    user_id INT,
    csr_data TEXT NOT NULL,
    status ENUM('pending', 'approved', 'rejected', 'issued') DEFAULT 'pending',
    certificate_id INT,
    approval_user_id INT,
    approval_date DATETIME,
    rejection_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (certificate_id) REFERENCES certificates(id) ON DELETE SET NULL,
    FOREIGN KEY (approval_user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_request_id (request_id),
    INDEX idx_status (status),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 插入默认管理员用户 (密码: admin123)
INSERT IGNORE INTO users (username, password_hash, email, role) VALUES
('admin', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'admin@ca.com', 'admin'),
('auditor', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'auditor@ca.com', 'auditor'),
('user1', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'user1@ca.com', 'user');

-- 创建存储过程：清理过期证书
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS cleanup_expired_certificates()
BEGIN
    UPDATE certificates 
    SET status = 'expired' 
    WHERE status = 'active' 
    AND validity_end < NOW();
END //
DELIMITER ;

-- 创建事件：每天清理过期证书
CREATE EVENT IF NOT EXISTS daily_certificate_cleanup
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_TIMESTAMP
DO
CALL cleanup_expired_certificates();

-- 创建视图：证书概览
CREATE VIEW IF NOT EXISTS certificate_overview AS
SELECT 
    c.serial_number,
    c.subject_name,
    c.issuer_name,
    c.validity_start,
    c.validity_end,
    c.status,
    COUNT(DISTINCT cr.id) as request_count
FROM certificates c
LEFT JOIN certificate_requests cr ON c.id = cr.certificate_id
GROUP BY c.id;

-- 设置事件调度器开启
SET GLOBAL event_scheduler = ON;