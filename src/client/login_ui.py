from PyQt5.QtWidgets import QWidget, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QMessageBox, QApplication
from PyQt5.QtCore import Qt
import asyncio
from crypto_gmssl import ClientGMSCrypto as CryptoManager


class LoginDialog(QDialog):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.crypto = CryptoManager()  # 初始化加密管理器
        self.init_ui()
        self.setup_ui()

    def init_ui(self):
        self.setWindowTitle('登录')
        self.setFixedSize(500, 400)

        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(0, 0, 0, 40)

        # 添加标题栏
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet('background-color: #f5f5f5; border-top-left-radius: 8px; border-top-right-radius: 8px;')
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(15, 0, 10, 0)

        # 标题
        title = QLabel('CA 系统登录')
        title.setStyleSheet(
            'font-family: "Microsoft YaHei", sans-serif; font-size: 16px; color: #333; font-weight: 500;')
        title_bar_layout.addWidget(title)

        # 窗口控制按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        min_btn = QPushButton('一')
        min_btn.setFixedSize(20, 20)
        min_btn.setStyleSheet('''
            QPushButton {
                background-color: transparent;
                border: none;
                font-family: "Microsoft YaHei", sans-serif;
                font-size: 12px;
                color: #666;
            }
            QPushButton:hover {
                background-color: #e5e5e5;
                border-radius: 2px;
            }
        ''')
        min_btn.clicked.connect(self.showMinimized)

        close_btn = QPushButton('×')
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet('''
            QPushButton {
                background-color: transparent;
                border: none;
                font-family: "Microsoft YaHei", sans-serif;
                font-size: 16px;
                color: #666;
            }
            QPushButton:hover {
                background-color: #ff4d4d;
                color: white;
                border-radius: 2px;
            }
        ''')
        close_btn.clicked.connect(self.close)

        btn_layout.addWidget(min_btn)
        btn_layout.addWidget(close_btn)
        title_bar_layout.addLayout(btn_layout)

        main_layout.addWidget(title_bar)

        # 内容布局
        content_layout = QVBoxLayout()
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(50, 20, 50, 20)

        # 标题标签
        title_label = QLabel('欢迎登录')
        title_label.setStyleSheet(
            'font-family: "Microsoft YaHei", sans-serif; font-size: 24px; font-weight: bold; color: #333; margin-bottom: 30px;')
        title_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(title_label)

        # 用户名输入
        username_layout = QHBoxLayout()
        username_layout.setSpacing(15)
        username_label = QLabel('用户名')
        username_label.setStyleSheet(
            'font-family: "Microsoft YaHei", sans-serif; font-size: 14px; color: #333; min-width: 60px;')
        username_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.username_input = QLineEdit()
        self.username_input.setStyleSheet('''
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                font-family: "Microsoft YaHei", sans-serif;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 1px solid #409eff;
                box-shadow: 0 0 0 2px rgba(64,158,255,.2);
            }
        ''')
        self.username_input.setMinimumWidth(250)
        self.username_input.setPlaceholderText('请输入用户名')
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        content_layout.addLayout(username_layout)

        # 密码输入
        password_layout = QHBoxLayout()
        password_layout.setSpacing(15)
        password_label = QLabel('密码')
        password_label.setStyleSheet(
            'font-family: "Microsoft YaHei", sans-serif; font-size: 14px; color: #333; min-width: 60px;')
        password_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet('''
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                font-family: "Microsoft YaHei", sans-serif;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 1px solid #409eff;
                box-shadow: 0 0 0 2px rgba(64,158,255,.2);
            }
        ''')
        self.password_input.setMinimumWidth(250)
        self.password_input.setPlaceholderText('请输入密码')
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        content_layout.addLayout(password_layout)

        # 登录按钮
        self.login_btn = QPushButton('登录')
        self.login_btn.setStyleSheet('''
            QPushButton {
                background-color: #409eff;
                color: white;
                border: none;
                padding: 10px;
                font-family: "Microsoft YaHei", sans-serif;
                font-size: 14px;
                border-radius: 4px;
                min-width: 200px;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #66b1ff;
            }
            QPushButton:pressed {
                background-color: #3a8ee6;
            }
        ''')
        self.login_btn.clicked.connect(self.start_login_task)
        content_layout.addWidget(self.login_btn, alignment=Qt.AlignCenter)

        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)

        # 设置窗口样式
        self.setStyleSheet('''
            QDialog {
                background-color: white;
                border: 1px solid #dcdfe6;
                border-radius: 8px;
            }
        ''')
        # 设置窗口无边框
        self.setWindowFlags(Qt.FramelessWindowHint)

        # 添加鼠标拖动支持
        self.oldPos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.oldPos:
            delta = event.globalPos() - self.oldPos
            self.move(self.pos() + delta)
            self.oldPos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.oldPos = None



    def start_login_task(self):
        try:
            username = self.username_input.text()
            password = self.password_input.text()
    
            if not username or not password:
                QMessageBox.warning(self, '警告', '请输入用户名和密码')
                return
    
            # 检查连接状态并尝试重新连接
            if not self.client.is_connected():
                QMessageBox.information(self, '提示', '正在尝试连接服务器...')
                if not self.client.connect():
                    QMessageBox.warning(self, '警告', '无法连接到服务器，请检查网络连接或服务器状态')
                    return
    
            # 禁用登录按钮
            self.login_btn.setEnabled(False)
            self.login_btn.setText('登录中...')
            QApplication.processEvents()  # 确保UI更新
    
            try:
                # 使用SM3对密码进行哈希处理
                password_hash = self.crypto.sm3_hash(password)
                
                # 发送登录请求，获取服务器公钥
                response = self.client.send_request('login', {
                    'username': username,
                    'password': password_hash
                })
                
                print(f"登录响应: {response}")
                
                if response and response.get('status') == 'success':
                    # 获取服务器公钥和用户信息
                    data = response.get('data', {})
                    server_public_key = data.get('server_public_key')
                    user_id = data.get('user_id')
                    username = data.get('username')
                    role = data.get('role')
                    
                    print(f"获取到服务器公钥: {server_public_key[:30] if server_public_key else 'None'}")
                    print(f"用户ID: {user_id}")
                    
                    # 如果服务器返回了公钥，保存它
                    if server_public_key:
                        if self.crypto.save_server_public_key(server_public_key):
                            print("服务器公钥保存成功")
                        else:
                            print("服务器公钥保存失败")
                    
                    # 保存用户信息到客户端实例
                    self.client.user_info = {
                        'user_id': user_id,
                        'username': username,
                        'role': role
                    }
                    
                    # 保存加密工具到客户端实例
                    self.client.crypto = self.crypto
                    
                    # 登录成功，关闭登录对话框
                    self.accept()
                else:
                    error_msg = response.get('message', '登录失败，请检查用户名和密码') if response else '登录失败，请稍后重试'
                    QMessageBox.warning(self, '错误', error_msg)
            except Exception as e:
                QMessageBox.critical(self, '错误', f'登录失败: {str(e)}')
            finally:
                # 恢复登录按钮状态
                self.login_btn.setEnabled(True)
                self.login_btn.setText('登录')
        except Exception as e:
            # 捕获所有可能的异常，确保程序不会崩溃
            print(f"登录过程中发生未知错误: {str(e)}")
            QMessageBox.critical(self, '错误', f'登录过程中发生未知错误: {str(e)}')
            # 确保按钮状态恢复
            try:
                self.login_btn.setEnabled(True)
                self.login_btn.setText('登录')
            except:
                pass



    def _handle_login_result(self, task):
        try:
            task.result()
        except Exception as e:
            QMessageBox.critical(self, '错误', f'登录失败: {str(e)}')
        finally:
            if self.client.loop.is_running():
                self.client.loop.call_soon_threadsafe(self.client.loop.stop)

    def closeEvent(self, event):
        if hasattr(self, '_login_task') and not self._login_task.done():
            self._login_task.cancel()
            try:
                self.client.loop.run_until_complete(self._login_task)
            except asyncio.CancelledError:
                pass
        event.accept()

    def setup_ui(self):
        # 初始化登录按钮状态
        self.login_btn.setEnabled(True)
        # 如果client有connection_status_changed信号，则连接它
        if hasattr(self.client, 'connection_status_changed'):
            self.client.connection_status_changed.connect(self.on_connection_status_changed)

    def on_connection_status_changed(self, is_connected):
        self.login_btn.setEnabled(is_connected)
        # 在UI中显示连接状态
        QMessageBox.information(self, '连接状态', '已连接到服务器' if is_connected else '未连接到服务器')

    # 修改登录按钮点击事件处理函数
    # def login(self):
    #     username = self.username_input.text().strip()
    #     password = self.password_input.text().strip()
        
    #     if not username or not password:
    #         QMessageBox.warning(self, "输入错误", "用户名和密码不能为空")
    #         return
            
    #     # 检查网络连接
    #     if not self.client.is_connected():
    #         try:
    #             self.client.connect()
    #         except Exception as e:
    #             QMessageBox.critical(self, "连接错误", f"无法连接到服务器: {str(e)}")
    #             return
        
    #     # 计算密码哈希
    #     password_hash = self.crypto.sm3_hash(password)
    #     if not password_hash:
    #         QMessageBox.critical(self, "加密错误", "计算密码哈希失败")
    #         return
            
    #     # 检查是否已有服务器公钥
    #     has_server_key = self.crypto.is_server_public_key_exists()
        
    #     # 构建登录请求
    #     login_data = {
    #         "username": username,
    #         "password": password_hash
    #     }
        
    #     # 如果已有服务器公钥，尝试加密会话密钥
    #     encrypted_session_key = None
    #     if has_server_key:
    #         server_public_key = self.crypto.get_server_public_key()
    #         if server_public_key:
    #             encrypted_session_key = self.crypto.encrypt_session_key(server_public_key)
    #             if encrypted_session_key:
    #                 login_data["session_key"] = encrypted_session_key
        
    #     # 发送登录请求
    #     request = {
    #         "action": "login",
    #         "data": login_data
    #     }
        
    #     try:
    #         # 发送请求并等待响应
    #         self.client.send_request(request)
            
    #         # 处理响应在response_received信号处理函数中
    #         self.waiting_for_login_response = True
            
    #     except Exception as e:
    #         QMessageBox.critical(self, "登录错误", f"发送登录请求失败: {str(e)}")
    
    # 添加处理登录响应的方法
    def handle_login_response(self, response):
        if not self.waiting_for_login_response:
            return
            
        self.waiting_for_login_response = False
        
        if response.get("status") != "success":
            error_msg = response.get("message", "未知错误")
            QMessageBox.warning(self, "登录失败", f"登录失败: {error_msg}")
            return
            
        # 登录成功
        user_data = response.get("data", {})
        
        # # 检查是否需要建立安全通信
        # if "server_public_key" in user_data:
        #     server_public_key = user_data["server_public_key"]
            
        #     # 提示用户是否建立安全通信
        #     reply = QMessageBox.question(
        #         self, 
        #         "安全通信", 
        #         "服务器请求建立安全通信，是否同意？\n拒绝将无法继续使用应用。",
        #         QMessageBox.Yes | QMessageBox.No,
        #         QMessageBox.Yes
        #     )
            
        if reply == QMessageBox.Yes:
            # 保存服务器公钥
            if not self.crypto.save_server_public_key(server_public_key):
                QMessageBox.critical(self, "错误", "保存服务器公钥失败")
                return
                    
                # # 加密会话密钥
                # encrypted_session_key = self.crypto.encrypt_session_key(server_public_key)
                # if not encrypted_session_key:
                #     QMessageBox.critical(self, "错误", "加密会话密钥失败")
                #     return
                    
                # # 发送会话密钥到服务器
                # establish_session_request = {
                #     "action": "establish_session",
                #     "data": {
                #         "user_id": user_data.get("user_id"),
                #         "session_key": encrypted_session_key
                #     }
                # }
                
                # try:
                #     # 发送请求并等待响应
                #     self.client.send_request(establish_session_request)
                #     self.waiting_for_session_response = True
                #     return
                    
                # except Exception as e:
                #     QMessageBox.critical(self, "错误", f"发送会话密钥失败: {str(e)}")
                #     return
            # else:
            #     # 用户拒绝建立安全通信
            #     QMessageBox.warning(self, "警告", "您拒绝了安全通信请求，应用将退出。")
            #     self.reject()  # 关闭登录对话框
            #     return
        
        # 如果不需要建立安全通信，直接完成登录
        self.accept()  # 关闭登录对话框并返回接受结果
    
    # # 添加处理会话建立响应的方法
    # def handle_session_response(self, response):
    #     if not self.waiting_for_session_response:
    #         return
            
    #     self.waiting_for_session_response = False
        
    #     if response.get("status") != "success":
    #         error_msg = response.get("message", "未知错误")
    #         QMessageBox.warning(self, "会话建立失败", f"建立安全会话失败: {error_msg}")
    #         return
            
    #     # 会话建立成功，完成登录
    #     QMessageBox.information(self, "登录成功", "安全会话已建立，登录成功！")
    #     self.accept()  # 关闭登录对话框并返回接受结果
        
    # # 修改响应处理函数，根据不同的响应类型调用不同的处理方法
    # def handle_response(self, response):
    #     # 根据响应中的action字段判断响应类型
    #     action = response.get("action", "")
        
    #     if action == "login" and self.waiting_for_login_response:
    #         self.handle_login_response(response)
    #     elif action == "establish_session" and self.waiting_for_session_response:
    #         self.handle_session_response(response)