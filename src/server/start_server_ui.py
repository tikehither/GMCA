import sys
import traceback
import socket

# 导入secure_logger
from secure_logger import secure_logger_manager as logger_manager

# 先测试PyQt5是否能正常工作
try:
    from PyQt5.QtWidgets import QApplication, QMessageBox, QMainWindow, QLabel
    from PyQt5.QtCore import QObject, pyqtSignal, Qt
    
    # 创建一个简单的测试应用
    test_app = QApplication.instance()
    if not test_app:
        test_app = QApplication([])
    
    logger_manager.log("PyQt5基本功能测试通过", "info")
except Exception as e:
    logger_manager.log(f"PyQt5测试失败: {str(e)}", "error")
    logger_manager.log(traceback.format_exc(), "error")
    sys.exit(1)

# 尝试导入server_ui模块
try:
    logger_manager.log("正在导入server_ui模块...", "info")
    from server_ui import main
    logger_manager.log("server_ui模块导入成功", "info")
except Exception as e:
    logger_manager.log(f"导入server_ui模块失败: {str(e)}", "error")
    logger_manager.log(traceback.format_exc(), "error")
    QMessageBox.critical(None, "错误", f"无法导入server_ui模块: {str(e)}")
    sys.exit(1)

import faulthandler
faulthandler.enable()

class LogRedirector(QObject):
    log_signal = pyqtSignal(str)

    def __init__(self, log_callback):
        super().__init__()
        self.log_callback = log_callback
        self.buffer = ""
        self.log_signal.connect(self.log_callback)

    def write(self, text):
        try:
            self.buffer += text
            if '\n' in self.buffer:
                lines = self.buffer.split('\n')
                for line in lines[:-1]:
                    if line.strip():  # 只输出非空行
                        logger_manager.log(line, "info")  # 使用secure_logger记录日志
                        self.log_signal.emit(line)
                self.buffer = lines[-1]
        except Exception as e:
            logger_manager.log(f"日志重定向错误: {str(e)}", "error")

    def flush(self):
        if self.buffer:
            logger_manager.log(self.buffer, "info")  # 使用secure_logger记录日志
            self.log_signal.emit(self.buffer)
            self.buffer = ""

def get_network_info():
    """获取本机网络信息，帮助诊断连接问题"""
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        # 记录网络信息到secure_logger
        logger_manager.log(f"主机名: {hostname}", "info")
        logger_manager.log(f"本地IP: {local_ip}", "info")
        
        # 返回格式化的网络信息字符串，但不显示在日志中
        return f"主机名: {hostname}, 本地IP: {local_ip}"
    except Exception as e:
        error_msg = f"获取网络信息失败: {str(e)}"
        logger_manager.log(error_msg, "error")
        return error_msg

from init_db import DatabaseInitializer

def init_database():
    """初始化数据库"""
    try:
        logger_manager.log("正在初始化数据库...", "info")
        initializer = DatabaseInitializer()
        initializer.init_database_with_retry()
        logger_manager.log("数据库初始化成功", "info")
    except Exception as e:
        error_msg = f"数据库初始化失败: {str(e)}\n{traceback.format_exc()}"
        logger_manager.log(error_msg, "error")
        QMessageBox.critical(None, "错误", error_msg)
        return False
    return True

def start_ui():
    app = None
    try:
        # 使用已存在的QApplication实例或创建新的
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)
            
        # 初始化数据库
        if not init_database():
            return 1
        
        logger_manager.log("正在初始化服务器UI...", "info")
        
        # 尝试初始化服务器UI，使用try/except捕获所有可能的异常
        try:
            logger_manager.log("调用main()函数...", "info")
            server_ui = main()
            logger_manager.log("main()函数调用成功", "info")
            
            if server_ui is None:
                logger_manager.log("服务器UI初始化失败！", "error")
                QMessageBox.critical(None, "错误", "服务器UI初始化失败，返回了None")
                return 1
        except Exception as e:
            error_msg = f"服务器UI初始化失败: {str(e)}\n{traceback.format_exc()}"
            logger_manager.log(error_msg, "error")
            QMessageBox.critical(None, "错误", error_msg)
            return 1
        
        logger_manager.log("正在设置日志重定向...", "info")
        # 创建日志重定向器
        try:
            stdout_redirector = LogRedirector(server_ui.append_log)
            stderr_redirector = LogRedirector(server_ui.append_log)
            
            # 重定向标准输出和标准错误到UI
            sys.stdout = stdout_redirector
            sys.stderr = stderr_redirector
        except Exception as e:
            error_msg = f"日志重定向设置失败: {str(e)}\n{traceback.format_exc()}"
            logger_manager.log(error_msg, "error")
            QMessageBox.warning(None, "警告", "日志重定向失败，将使用控制台输出")
        
        # 尝试获取网络信息
        try:
            logger_manager.log("系统网络信息:", "info")
            network_info = get_network_info()
            # 不在日志中显示网络信息，但仍然获取它用于其他用途
            # logger_manager.log(network_info, "info")
            logger_manager.log("请确保客户端使用正确的IP地址和端口连接服务器", "info")
        except Exception as e:
            logger_manager.log(f"获取网络信息失败: {str(e)}", "error")
        
        logger_manager.log("正在显示UI界面...", "info")
        # 显示并激活窗口
        try:
            server_ui.show()
            server_ui.setWindowState(server_ui.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
            server_ui.raise_()
            server_ui.activateWindow()
            
            # 将窗口移动到屏幕中央
            screen = app.primaryScreen().geometry()
            window_geometry = server_ui.geometry()
            x = (screen.width() - window_geometry.width()) // 2
            y = (screen.height() - window_geometry.height()) // 2
            server_ui.move(x, y)
        except Exception as e:
            error_msg = f"窗口显示失败: {str(e)}\n{traceback.format_exc()}"
            logger_manager.log(error_msg, "error")
            QMessageBox.warning(None, "警告", "窗口显示异常，但程序将继续运行")
        
        logger_manager.log("UI界面初始化完成，开始运行事件循环...", "info")
        return app.exec_()
    except Exception as e:
        error_msg = f"UI启动过程中发生错误: {str(e)}\n详细错误信息:\n{traceback.format_exc()}"
        logger_manager.log(error_msg, "error")
        QMessageBox.critical(None, "严重错误", error_msg)
        return 1

if __name__ == '__main__':
    try:
        sys.exit(start_ui())
    except Exception as e:
        error_msg = f"发生错误: {str(e)}\n详细错误信息:\n{traceback.format_exc()}"
        logger_manager.log(error_msg, "error")
        QMessageBox.critical(None, "严重错误", error_msg)
        input("按回车键退出...")
        sys.exit(1)