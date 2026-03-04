from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, \
    QApplication, QLineEdit, QTextEdit, QMessageBox, QTabWidget, QComboBox, QFileDialog, QDialog, \
    QGroupBox, QFormLayout, QTableWidget, QHeaderView, QTableWidgetItem
from PyQt5.QtCore import Qt
import os
import asyncio


class CAClient(QMainWindow):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.client.response_received.connect(self.handle_response)
        self.client.error_occurred.connect(self.handle_error)
        # 从client实例获取用户信息
        self.user_info = getattr(client, 'user_info', None)
        # 从client实例获取加密工具
        self.crypto = getattr(client, 'crypto', None)
        # 默认密钥和证书保存路径
        self.key_save_dir = os.path.join(os.path.expanduser('~'), '.ca_client')
        self.cert_save_dir = os.path.join(self.key_save_dir, 'certificates')
        self.init_ui()

        # 设置窗口居中显示
        screen = QApplication.primaryScreen().geometry()
        window_geometry = self.geometry()
        x = (screen.width() - window_geometry.width()) // 2
        y = (screen.height() - window_geometry.height()) // 2
        self.move(x, y)

    def init_ui(self):
        self.setWindowTitle('CA客户端')
        self.setGeometry(100, 100, 800, 600)

        # 创建标签页
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # 证书申请页
        self.apply_tab = QWidget()
        self.init_apply_tab()
        self.tabs.addTab(self.apply_tab, '证书申请')

        # 证书验证页
        self.verify_tab = QWidget()
        self.init_verify_tab()
        self.tabs.addTab(self.verify_tab, '证书验证')

        
        # 个人信息页
        self.profile_tab = QWidget()
        self.init_profile_tab()
        self.tabs.addTab(self.profile_tab, '个人信息')

    #async def get_certificate_templates(self, user_id=None):
    #    """
    #    获取证书模板列表
    
    #    Args:
    #        user_id: 可选，用户ID，用于筛选用户有权限使用的模板
        
    #    Returns:
    #        成功返回模板列表，失败返回None
    #    """
    #    try:
    #        # 构建请求数据
    #        request_data = {'user_id': user_id} if user_id else {}
            
    #        # 发送请求到服务器
    #        response = await asyncio.to_thread(self.client.send_request, 'get_certificate_templates', request_data)
        
    #        # 检查响应状态
    #        if response and response.get('status') == 'success':
    #            # 返回模板列表
    #            return response.get('data', {}).get('templates', [])
    #        else:
    #            # 获取失败，记录错误信息
    #            error_msg = response.get('message', '未知错误') if response else '服务器无响应'
    #            print(f"获取证书模板失败: {error_msg}")
    #            return None
            
    #    except Exception as e:
    #        print(f"获取证书模板过程发生错误: {str(e)}")
    #        import traceback
    #        traceback.print_exc()
    #        return None

    async def async_init(self):
        # 加载证书模板
        await self.load_certificate_templates()

    async def load_certificate_templates(self):
        """加载证书模板列表"""
        try:
            # 发送获取模板列表的请求
            response = await asyncio.to_thread(self.client.send_request, 'get_certificate_templates', {})

            if response and response.get('status') == 'success':
                templates = response.get('data', [])
                self.update_templates(templates)
            else:
                error_msg = response.get('message', '获取证书模板失败') if response else '获取证书模板失败，请稍后重试'
                print(f"加载证书模板失败: {error_msg}")
        except Exception as e:
            print(f"加载证书模板时发生错误: {str(e)}")

    def init_apply_tab(self):
        layout = QVBoxLayout()

        # 证书模板选择
        template_layout = QHBoxLayout()
        template_label = QLabel('证书模板:')
        self.template_combo = QComboBox()
        self.template_combo.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                min-width: 200px;
            }
            QComboBox:hover {
                border-color: #409eff;
            }
        """)
        template_layout.addWidget(template_label)
        template_layout.addWidget(self.template_combo)
        layout.addLayout(template_layout)

        # 主题名称输入
        subject_layout = QHBoxLayout()
        subject_label = QLabel('主题名称:')
        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText('请输入证书主题名称')
        self.subject_input.setStyleSheet("""
            QLineEdit {
                padding: 5px;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                min-width: 200px;
            }
            QLineEdit:focus {
                border-color: #409eff;
            }
        """)
        subject_layout.addWidget(subject_label)
        subject_layout.addWidget(self.subject_input)
        layout.addLayout(subject_layout)

        # 公钥输入
        pubkey_layout = QHBoxLayout()
        pubkey_label = QLabel('公钥:')
        self.pubkey_input = QTextEdit()
        self.pubkey_input.setPlaceholderText('公钥将在生成密钥对后自动填充')
        self.pubkey_input.setStyleSheet("""
            QTextEdit {
                padding: 5px;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                min-height: 100px;
            }
            QTextEdit:focus {
                border-color: #409eff;
            }
        """)
        pubkey_layout.addWidget(pubkey_label)
        pubkey_layout.addWidget(self.pubkey_input)
        layout.addLayout(pubkey_layout)

        # 密钥管理按钮组
        key_group = QHBoxLayout()
        self.generate_key_btn = QPushButton('生成密钥对')
        self.generate_key_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #409eff;
                color: white;
                border: none;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #66b1ff;
            }
            QPushButton:pressed {
                background-color: #3a8ee6;
            }
        """)
        self.generate_key_btn.clicked.connect(self.generate_key_pair)
        
        self.save_key_btn = QPushButton('保存密钥')
        self.save_key_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #67c23a;
                color: white;
                border: none;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #85ce61;
            }
            QPushButton:pressed {
                background-color: #5daf34;
            }
        """)
        self.save_key_btn.clicked.connect(self.save_key_pair)
        
        key_group.addWidget(self.generate_key_btn)
        key_group.addWidget(self.save_key_btn)
        layout.addLayout(key_group)

        # 申请和下载按钮组
        action_group = QHBoxLayout()
        self.apply_btn = QPushButton('申请证书')
        self.apply_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #409eff;
                color: white;
                border: none;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #66b1ff;
            }
            QPushButton:pressed {
                background-color: #3a8ee6;
            }
        """)
        self.apply_btn.clicked.connect(lambda: self.run_async_task(self.apply_certificate))
        
        self.download_btn = QPushButton('下载证书')
        self.download_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #67c23a;
                color: white;
                border: none;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #85ce61;
            }
            QPushButton:pressed {
                background-color: #5daf34;
            }
        """)
        self.download_btn.clicked.connect(lambda: self.run_async_task(self.download_certificate))
        
        action_group.addWidget(self.apply_btn)
        action_group.addWidget(self.download_btn)
        layout.addLayout(action_group)

        # 结果显示
        self.apply_result = QTextEdit()
        self.apply_result.setReadOnly(True)
        self.apply_result.setStyleSheet("""
            QTextEdit {
                padding: 5px;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                min-height: 150px;
                background-color: #f5f7fa;
            }
        """)
        layout.addWidget(self.apply_result)

        self.apply_tab.setLayout(layout)

    def init_verify_tab(self):
        layout = QVBoxLayout()

        # 序列号输入
        serial_layout = QHBoxLayout()
        serial_label = QLabel('证书序列号:')
        self.verify_serial_input = QLineEdit()
        serial_layout.addWidget(serial_label)
        serial_layout.addWidget(self.verify_serial_input)
        layout.addLayout(serial_layout)

        # 验证按钮
        self.verify_btn = QPushButton('验证证书')
        self.verify_btn.clicked.connect(lambda: self.run_async_task(self.verify_certificate))
        layout.addWidget(self.verify_btn)

        # 结果显示
        self.verify_result = QTextEdit()
        self.verify_result.setReadOnly(True)
        layout.addWidget(self.verify_result)

        self.verify_tab.setLayout(layout)

  
    def show_change_password_dialog(self):
        """显示修改密码对话框"""
        try:
            dialog = ChangePasswordDialog(self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, '错误', f'显示修改密码对话框失败: {str(e)}')

    def init_profile_tab(self):
        layout = QVBoxLayout()
        
        # 添加个人信息相关的UI组件
        info_label = QLabel('个人信息管理')
        info_label.setStyleSheet('font-size: 16px; font-weight: bold; margin-bottom: 10px;')
        layout.addWidget(info_label)
        
        # 用户基本信息组
        info_group = QGroupBox('基本信息')
        info_layout = QFormLayout()
        
        # 用户名
        self.username_label = QLabel()
        self.username_label.setStyleSheet('padding: 5px;')
        info_layout.addRow('用户名:', self.username_label)
        
        # 角色
        self.role_label = QLabel()
        self.role_label.setStyleSheet('padding: 5px;')
        info_layout.addRow('角色:', self.role_label)
        
        # 注册时间
        self.register_time_label = QLabel()
        self.register_time_label.setStyleSheet('padding: 5px;')
        info_layout.addRow('注册时间:', self.register_time_label)
        
        # 最后登录时间
        self.last_login_label = QLabel()
        self.last_login_label.setStyleSheet('padding: 5px;')
        info_layout.addRow('最后登录:', self.last_login_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 证书申请记录组
        cert_group = QGroupBox('证书申请记录')
        cert_layout = QVBoxLayout()
        
        # 创建证书申请表格
        self.cert_table = QTableWidget()
        self.cert_table.setColumnCount(6)
        self.cert_table.setHorizontalHeaderLabels(['序列号', '主题名称', '申请时间', '状态', '用途', '操作'])
        self.cert_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        cert_layout.addWidget(self.cert_table)
        
        # 刷新按钮
        refresh_btn = QPushButton('刷新申请记录')
        refresh_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #409eff;
                color: white;
                border: none;
                border-radius: 4px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #66b1ff;
            }
            QPushButton:pressed {
                background-color: #3a8ee6;
            }
        """)
        refresh_btn.clicked.connect(lambda: self.run_async_task(self.load_certificate_applications))
        cert_layout.addWidget(refresh_btn, alignment=Qt.AlignCenter)
        
        cert_group.setLayout(cert_layout)
        layout.addWidget(cert_group)
        
        # 密码管理组
        password_group = QGroupBox('密码管理')
        password_layout = QVBoxLayout()
        
        # 修改密码按钮
        self.change_password_btn = QPushButton('修改密码')
        self.change_password_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #409eff;
                color: white;
                border: none;
                border-radius: 4px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #66b1ff;
            }
            QPushButton:pressed {
                background-color: #3a8ee6;
            }
        """)
        self.change_password_btn.clicked.connect(self.show_change_password_dialog)
        password_layout.addWidget(self.change_password_btn, alignment=Qt.AlignCenter)
        
        password_group.setLayout(password_layout)
        layout.addWidget(password_group)
        
        # 添加弹性空间
        layout.addStretch()
        
        self.profile_tab.setLayout(layout)
        
        # 加载用户信息
        self.load_user_info()
        
        # 加载证书申请记录
        self.run_async_task(self.load_certificate_applications)


    def generate_key_pair(self):
        try:
            # 使用CryptoManager生成密钥对
            from crypto_gmssl import ClientGMSCrypto as CryptoManager
            
            # 如果client中有crypto实例，使用它；否则创建新的
            if self.crypto:
                crypto_manager = self.crypto
            else:
                crypto_manager = CryptoManager()
            
            # 先检查是否已经存在密钥
            private_key, public_key = crypto_manager.load_or_generate_sm2_key_pair()

            self.private_key = private_key
            self.public_key = public_key
            self.pubkey_input.setText(public_key)
            
            # 保存crypto_manager实例以便后续使用
            self.crypto_manager = crypto_manager
            
            QMessageBox.information(self, '成功', '密钥对已加载或生成成功！')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'生成密钥对失败: {str(e)}')

    def save_key_pair(self):
        try:
            if not hasattr(self, 'private_key') or not hasattr(self, 'public_key'):
                QMessageBox.warning(self, '警告', '请先生成密钥对')
                return

            # 打开文件夹选择对话框
            directory = QFileDialog.getExistingDirectory(self, '选择密钥保存目录', self.key_save_dir)
            if not directory:  # 如果用户取消选择
                return
                
            # 使用用户选择的目录
            save_dir = directory
            
            # 如果有crypto_manager实例，使用它的保存方法
            if hasattr(self, 'crypto_manager'):
                self.crypto_manager.save_sm2_key_pair(save_dir)
                # 同时保存SM4密钥
                self.crypto_manager.save_sm4_key(save_dir)
            else:
                # 兼容旧方式，直接保存文件
                os.makedirs(save_dir, exist_ok=True)
                # 保存私钥
                private_key_path = os.path.join(save_dir, 'private.key')
                with open(private_key_path, 'w') as f:
                    f.write(self.private_key)
                # 保存公钥
                public_key_path = os.path.join(save_dir, 'public.key')
                with open(public_key_path, 'w') as f:
                    f.write(self.public_key)

            # 更新默认保存路径
            self.key_save_dir = save_dir
            
            QMessageBox.information(self, '成功', f'密钥对已保存到：\n{save_dir}')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'保存密钥对失败: {str(e)}')

    def set_cert_save_path(self):
        """设置证书保存路径"""
        try:
            # 打开文件夹选择对话框
            directory = QFileDialog.getExistingDirectory(self, '选择证书保存目录', self.cert_save_dir)
            if directory:  # 如果用户选择了目录
                self.cert_save_dir = directory
                QMessageBox.information(self, '成功', f'证书保存路径已设置为：\n{self.cert_save_dir}')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'设置证书保存路径失败: {str(e)}')

    async def download_certificate(self):
        try:
            serial_number = self.verify_serial_input.text()
            if not serial_number:
                QMessageBox.warning(self, '警告', '请先验证证书并获取序列号')
                return

            # 发送下载请求
            response = await asyncio.to_thread(self.client.send_request, 'download_certificate', {
                'serial_number': serial_number
            })

            if response and response.get('status') == 'success':
                cert_data = response.get('data', {})
                cert_content = cert_data.get('content')
                if cert_content:
                    # 打开文件夹选择对话框
                    directory = QFileDialog.getExistingDirectory(self, '选择证书保存目录', self.cert_save_dir)
                    if not directory:  # 如果用户取消选择
                        return
                        
                    # 使用用户选择的目录
                    save_dir = directory
                    os.makedirs(save_dir, exist_ok=True)

                    # 保存证书文件
                    cert_path = os.path.join(save_dir, f'cert_{serial_number}.cer')
                    with open(cert_path, 'w') as f:
                        f.write(cert_content)

                    # 更新默认保存路径
                    self.cert_save_dir = save_dir
                    
                    # 更新结果显示，包含保存路径信息
                    cert_save_path = os.path.abspath(cert_path)
                    key_save_path = os.path.abspath(self.key_save_dir)
                    
                    self.verify_result.setText(
                        f"证书下载成功！\n\n"
                        f"证书序列号: {serial_number}\n"
                        f"主题名称: {cert_data.get('subject_name', '未知')}\n\n"
                        f"证书已保存到: {cert_save_path}\n\n"
                        f"密钥保存位置: {key_save_path}\n"
                        f"(private.key 和 public.key)"
                    )
                    
                    # 显示更详细的成功消息，包括完整路径
                    QMessageBox.information(self, '成功', 
                        f'证书已成功下载！\n\n'
                        f'证书保存位置：\n{cert_save_path}\n\n'
                        f'密钥保存位置：\n{key_save_path}\n(private.key 和 public.key)')
                else:
                    QMessageBox.warning(self, '失败', '证书内容为空')
            else:
                error_msg = response.get('message', '下载证书失败') if response else '下载证书失败，请稍后重试'
                QMessageBox.warning(self, '失败', error_msg)

        except Exception as e:
            QMessageBox.critical(self, '错误', f'下载证书失败: {str(e)}')

    async def load_certificate_applications(self):
        """加载用户的证书申请记录"""
        try:
            # 确保用户已登录并获取用户ID
            if not self.user_info or not self.user_info.get('user_id'):
                QMessageBox.warning(self, '警告', '请先登录后再查看证书申请记录')
                return
                
            user_id = self.user_info.get('user_id')
            
            # 发送获取证书申请记录的请求，包含用户ID
            response = await asyncio.to_thread(self.client.send_request, 'get_certificate_applications', {
                'user_id': user_id
            })
            
            if response and response.get('status') == 'success':
                applications = response.get('data', [])
                
                # 清空表格
                self.cert_table.setRowCount(0)
                
                # 填充表格
                for i, app in enumerate(applications):
                    self.cert_table.insertRow(i)
                    
                    # 序列号
                    self.cert_table.setItem(i, 0, QTableWidgetItem(app.get('serial_number', '未知')))
                    
                    # 主题名称
                    subject = app.get('subject_name', '未知')
                    if 'CN=' in subject:
                        subject = subject.split('CN=')[1].split(',')[0]
                    self.cert_table.setItem(i, 1, QTableWidgetItem(subject))
                    
                    # 申请时间
                    self.cert_table.setItem(i, 2, QTableWidgetItem(app.get('submit_date', '未知')))
                    
                    # 状态
                    status = app.get('status', 'unknown')
                    status_text = {
                        'pending': '待审核',
                        'approved': '已批准',
                        'rejected': '已拒绝',
                        'valid': '有效',
                        'revoked': '已撤销'
                    }.get(status, '未知')
                    status_item = QTableWidgetItem(status_text)
                    
                    # 根据状态设置背景色
                    if status == 'pending':
                        status_item.setBackground(Qt.yellow)
                    elif status in ('approved', 'valid'):
                        status_item.setBackground(Qt.green)
                    elif status in ('rejected', 'revoked'):
                        status_item.setBackground(Qt.red)
                    
                    self.cert_table.setItem(i, 3, status_item)
                    
                    # 用途
                    self.cert_table.setItem(i, 4, QTableWidgetItem(app.get('usage', '未知')))
                    
                    # 操作按钮
                    if status in ('approved', 'valid'):
                        action_text = '下载'
                    else:
                        action_text = '查看'
                    self.cert_table.setItem(i, 5, QTableWidgetItem(action_text))
                
                # 连接表格单元格点击事件
                self.cert_table.cellClicked.connect(self.handle_cert_table_click)
                
            else:
                error_msg = response.get('message', '获取证书申请记录失败') if response else '获取证书申请记录失败，请稍后重试'
                QMessageBox.warning(self, '警告', error_msg)
        except Exception as e:
            QMessageBox.critical(self, '错误', f'加载证书申请记录失败: {str(e)}')

    def handle_cert_table_click(self, row, column):
        """处理证书表格单元格点击事件"""
        try:
            # 如果点击的是操作列
            if column == 5:
                serial_number = self.cert_table.item(row, 0).text()
                action_text = self.cert_table.item(row, 5).text()
                
                if action_text == '下载':
                    # 设置验证页的序列号输入框
                    self.verify_serial_input.setText(serial_number)
                    # 切换到验证页
                    self.tabs.setCurrentWidget(self.verify_tab)
                    # 执行下载操作
                    self.run_async_task(self.download_certificate)
                else:  # 查看
                    # 发送查看证书申请详情的请求
                    self.run_async_task(lambda: self.view_certificate_application(serial_number))
        except Exception as e:
            QMessageBox.critical(self, '错误', f'处理表格点击事件失败: {str(e)}')
            
    def load_user_info(self):
        """加载用户信息并更新UI"""
        try:
            # 检查是否有用户信息
            if not self.user_info:
                # 如果没有用户信息，可能是未登录状态
                self.username_label.setText('未登录')
                self.role_label.setText('未知')
                self.register_time_label.setText('--')
                self.last_login_label.setText('--')
                return
            
            # 更新UI显示
            self.username_label.setText(self.user_info.get('username', '未知'))
            
            # 角色显示
            role = self.user_info.get('role', 'user')
            role_text = '管理员' if role == 'admin' else '普通用户'
            self.role_label.setText(role_text)
            
            # 注册时间
            register_time = self.user_info.get('created_at', '--')
            self.register_time_label.setText(register_time)
            
            # 最后登录时间
            last_login = self.user_info.get('last_login', '--')
            self.last_login_label.setText(last_login)
            
        except Exception as e:
            QMessageBox.critical(self, '错误', f'加载用户信息失败: {str(e)}')

    # async def view_certificate_application(self, serial_number):
    #     """查看证书申请详情"""
    #     try:
    #         # 发送获取证书申请详情的请求
    #         response = await asyncio.to_thread(self.client.send_request, 'get_certificate_application', {
    #             'serial_number': serial_number
    #         })
            
    #         if response and response.get('status') == 'success':
    #             app_data = response.get('data', {})
                
    #             # 显示详情对话框
    #             detail_dialog = QDialog(self)
    #             detail_dialog.setWindowTitle('证书申请详情')
    #             detail_dialog.setFixedSize(500, 400)
                
    #             layout = QVBoxLayout()
                
    #             # 创建表单布局显示详情
    #             form_group = QGroupBox('申请信息')
    #             form_layout = QFormLayout()
                
    #             # 序列号
    #             form_layout.addRow('序列号:', QLabel(app_data.get('serial_number', '未知')))
                
    #             # 主题名称
    #             form_layout.addRow('主题名称:', QLabel(app_data.get('subject_name', '未知')))
                
    #             # 申请时间
    #             form_layout.addRow('申请时间:', QLabel(app_data.get('submit_date', '未知')))
                
    #             # 状态
    #             status = app_data.get('status', 'unknown')
    #             status_text = {
    #                 'pending': '待审核',
    #                 'approved': '已批准',
    #                 'rejected': '已拒绝',
    #                 'valid': '有效',
    #                 'revoked': '已撤销'
    #             }.get(status, '未知')
    #             form_layout.addRow('状态:', QLabel(status_text))
                
    #             # 组织机构
    #             form_layout.addRow('组织机构:', QLabel(app_data.get('organization', '未填写')))
                
    #             # 部门
    #             form_layout.addRow('部门:', QLabel(app_data.get('department', '未填写')))
                
    #             # 邮箱
    #             form_layout.addRow('邮箱:', QLabel(app_data.get('email', '未填写')))
                
    #             # 用途
    #             form_layout.addRow('用途:', QLabel(app_data.get('usage', '未填写')))
                
    #             # 备注
    #             form_layout.addRow('备注:', QLabel(app_data.get('remarks', '无')))
                
    #             form_group.setLayout(form_layout)
    #             layout.addWidget(form_group)
                
    #             # 关闭按钮
    #             close_btn = QPushButton('关闭')
    #             close_btn.clicked.connect(detail_dialog.accept)
    #             layout.addWidget(close_btn, alignment=Qt.AlignCenter)
                
    #             detail_dialog.setLayout(layout)
    #             detail_dialog.exec_()
    #         else:
    #             error_msg = response.get('message', '获取证书申请详情失败') if response else '获取证书申请详情失败，请稍后重试'
    #             QMessageBox.warning(self, '警告', error_msg)
    #     except Exception as e:
    #         QMessageBox.critical(self, '错误', f'查看证书申请详情失败: {str(e)}')

    def handle_response(self, response):
        if not response:
            return

        try:
            if response.get('status') == 'success':
                # 处理证书模板列表响应
                if 'templates' in response.get('data', {}):
                    self.update_templates(response['data']['templates'])
                # 处理证书信息响应
                elif 'certificate' in response.get('data', {}):
                    self.update_certificate_info(response['data']['certificate'])
                # 处理证书审核通过响应
                elif response.get('message') == '证书审核已通过' and 'serial_number' in response.get('data', {}):
                    serial_number = response['data']['serial_number']
                    QMessageBox.information(self, '成功', f'证书 {serial_number} 已审核通过！')
                    # 刷新证书申请记录
                    self.run_async_task(self.load_certificate_applications)
            else:
                QMessageBox.warning(self, '警告', response.get('message', '操作失败'))
        except Exception as e:
            QMessageBox.critical(self, '错误', f'处理响应失败: {str(e)}')
    
    def handle_error(self, error_msg):
        QMessageBox.critical(self, '错误', error_msg)

    def update_templates(self, templates):
        try:
            self.template_combo.clear()
            if not templates:
                return
            
            # 确保templates是列表类型
            if not isinstance(templates, list):
                if isinstance(templates, dict):
                    templates = templates.get('templates', [])
                else:
                    templates = []
            
            # 遍历模板列表并添加到下拉框
            for template in templates:
                if isinstance(template, dict):
                    template_id = template.get('id')
                    template_name = template.get('name')
                    if template_id is not None and template_name:
                        self.template_combo.addItem(template_name, template_id)
        except Exception as e:
            QMessageBox.critical(self, '错误', f'更新模板列表失败: {str(e)}')

    def update_certificate_info(self, cert_info):
        try:
            info_text = f"证书信息：\n"
            info_text += f"序列号: {cert_info.get('serial_number', '未知')}\n"
            info_text += f"主题: {cert_info.get('subject', '未知')}\n"
            info_text += f"状态: {cert_info.get('status', '未知')}\n"
            info_text += f"有效期: {cert_info.get('valid_from', '未知')} 至 {cert_info.get('valid_to', '未知')}"
            
            if self.tabs.currentWidget() == self.verify_tab:
                self.verify_result.setText(info_text)
            elif self.tabs.currentWidget() == self.apply_tab:
                self.apply_result.setText(info_text)
        except Exception as e:
            QMessageBox.critical(self, '错误', f'更新证书信息失败: {str(e)}')
            

    def run_async_task(self, async_func):
        """运行异步任务的辅助方法"""
        try:
            # 不使用事件循环嵌套，而是直接使用同步方式调用
            # 对于需要异步执行的操作，使用线程池或直接调用同步方法
            if asyncio.iscoroutinefunction(async_func):
                # 如果是协程函数，使用同步方式执行
                # 创建一个新的事件循环来运行协程
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    # 运行协程并等待完成
                    result = loop.run_until_complete(async_func())
                    # 确保所有待处理的任务都已完成
                    pending = asyncio.all_tasks(loop)
                    if pending:
                        loop.run_until_complete(asyncio.gather(*pending))
                finally:
                    # 关闭事件循环前停止它
                    loop.stop()
                    loop.close()
            else:
                # 如果是普通函数，直接调用
                async_func()
        except Exception as e:
            QMessageBox.critical(self, '错误', f'执行任务失败: {str(e)}')
            # 不再抛出异常，避免程序崩溃
            # raise e

    async def apply_certificate(self):
        """处理证书申请"""
        try:
            # 检查是否已生成密钥对
            if not hasattr(self, 'public_key') or not self.public_key:
                QMessageBox.warning(self, '警告', '请先生成密钥对')
                return
                
            # 获取当前选择的证书模板
            current_index = self.template_combo.currentIndex()
            if current_index < 0:
                QMessageBox.warning(self, '警告', '请选择证书模板')
                return
                
            template_id = self.template_combo.itemData(current_index)
            template_name = self.template_combo.currentText()
            
            # 打开证书申请对话框
            dialog = self.open_certificate_application_dialog(template_id, template_name)
            result = dialog.exec_()
            
            if result == QDialog.Accepted:
                # 对话框中的提交按钮会调用submit_certificate_application方法
                pass
            else:
                self.apply_result.setText("证书申请已取消")
                
        except Exception as e:
            QMessageBox.critical(self, '错误', f'申请证书失败: {str(e)}')
            
    def submit_certificate_application(self, application_data):
        """提交证书申请"""
        try:
            # 检查是否已生成密钥对
            if not hasattr(self, 'public_key') or not self.public_key:
                QMessageBox.warning(self, '警告', '请先生成密钥对')
                return
            
            # 提示用户保存密钥对
            reply = QMessageBox.question(self, '保存密钥对', 
                                        '在提交证书申请前，建议先保存您的密钥对。\n'
                                        '私钥将存储在本地，用于后续证书操作。\n'
                                        '是否现在保存密钥对？',
                                        QMessageBox.Yes | QMessageBox.No, 
                                        QMessageBox.Yes)
            
            if reply == QMessageBox.Yes:
                # 打开文件夹选择对话框
                directory = QFileDialog.getExistingDirectory(self, '选择密钥保存目录', self.key_save_dir)
                if directory:  # 如果用户选择了目录
                    save_dir = directory
                    
                    # 使用crypto_manager保存密钥对
                    if hasattr(self, 'crypto_manager') and self.crypto_manager:
                        self.crypto_manager.save_sm2_key_pair(save_dir)
                        self.crypto_manager.save_sm4_key(save_dir)
                    elif hasattr(self, 'private_key') and hasattr(self, 'public_key'):
                        # 兼容旧方式，直接保存文件
                        os.makedirs(save_dir, exist_ok=True)
                        # 保存私钥
                        private_key_path = os.path.join(save_dir, 'client_private.key')
                        with open(private_key_path, 'w') as f:
                            f.write(self.private_key)
                        # 保存公钥
                        public_key_path = os.path.join(save_dir, 'client_public.key')
                        with open(public_key_path, 'w') as f:
                            f.write(self.public_key)
                        QMessageBox.information(self, '成功', f'密钥对已保存到: {save_dir}')
                    else:
                        QMessageBox.warning(self, '警告', '无法保存密钥对：未找到密钥数据')
            
            # 确保有crypto_manager实例
            if not hasattr(self, 'crypto_manager'):
                # 如果client中有crypto实例，使用它；否则创建新的
                if self.crypto:
                    self.crypto_manager = self.crypto
                else:
                    from crypto_gmssl import ClientGMSCrypto as CryptoManager
                    self.crypto_manager = CryptoManager()
            
            # 构建主题名称字符串 (Distinguished Name)
            subject_name = f"CN={application_data['applicant_name']}"
            if application_data['organization']:
                subject_name += f",O={application_data['organization']}"
            if application_data['department']:
                subject_name += f",OU={application_data['department']}"
            if application_data['email']:
                subject_name += f",emailAddress={application_data['email']}"
            subject_name += ",C=CN"  # 默认国家为中国
            
            # 构建申请数据
            request_data = {
                'template_id': application_data['template_id'],
                'subject_name': subject_name,  # 发送格式化的主题名称
                'public_key': self.public_key,  # 发送公钥
                'organization': application_data['organization'],
                'department': application_data['department'],
                'email': application_data['email'],
                'usage': application_data['usage'],
                'remarks': application_data['remarks'],
                'user_id': self.user_info.get('user_id') if hasattr(self, 'user_info') and self.user_info else None  # 添加用户ID
            }
            
            self.apply_result.setText("正在提交证书申请...")
            
            # 直接使用同步方式发送请求，避免事件循环嵌套
            response = self.client.send_request('apply_certificate', request_data)
            
            if response and response.get('status') == 'success':
                cert_data = response.get('data', {})
                
                # 显示成功信息
                self.apply_result.setText(
                    f"证书申请成功！\n\n"
                    f"证书序列号: {cert_data.get('serial_number', '未知')}\n"
                    f"主题名称: {cert_data.get('subject_name', subject_name)}\n"
                    f"状态: {cert_data.get('status', '待审核')}\n"
                    f"申请时间: {cert_data.get('issue_date', '未知')}"
                )
                
                # 简单提示成功，不需要下载证书申请
                QMessageBox.information(self, '成功', '证书申请已提交，等待服务器审核！')
            else:
                error_msg = response.get('message', '申请失败') if response else '申请失败，请稍后重试'
                self.apply_result.setText(f"证书申请失败：{error_msg}")
                QMessageBox.warning(self, '失败', error_msg)
            
        except Exception as e:
            QMessageBox.critical(self, '错误', f'提交证书申请失败: {str(e)}')

    def open_certificate_application_dialog(self, template_id, template_name):
        """打开证书申请对话框"""
        try:
            # 创建证书申请对话框
            class CertificateApplicationDialog(QDialog):
                def __init__(self, parent=None, template_id=None, template_name=None):
                    super().__init__(parent)
                    self.parent = parent
                    self.template_id = template_id
                    self.template_name = template_name
                    self.init_ui()
                
                def init_ui(self):
                    self.setWindowTitle('证书申请')
                    self.setFixedSize(500, 500)
                    
                    # 创建主布局
                    main_layout = QVBoxLayout()
                    main_layout.setSpacing(15)
                    main_layout.setContentsMargins(20, 20, 20, 20)
                
                    # 标题
                    title_label = QLabel('证书申请表单')
                    title_label.setStyleSheet('font-size: 18px; font-weight: bold; margin-bottom: 10px;')
                    title_label.setAlignment(Qt.AlignCenter)
                    main_layout.addWidget(title_label)
                    
                    # 表单布局
                    form_group = QGroupBox('申请信息')
                    form_layout = QFormLayout()
                    form_layout.setVerticalSpacing(15)
                    form_layout.setHorizontalSpacing(20)
                
                    # 证书模板信息
                    self.template_label = QLabel(self.template_name or '未选择模板')
                    self.template_label.setStyleSheet("""
                        QLabel {
                            padding: 8px;
                            background-color: #f5f7fa;
                            border: 1px solid #dcdfe6;
                            border-radius: 4px;
                        }
                    """)
                    form_layout.addRow('证书模板:', self.template_label)
                
                    # 申请人姓名
                    self.applicant_name = QLineEdit()
                    self.applicant_name.setPlaceholderText('请输入申请人姓名')
                    self.applicant_name.setStyleSheet("""
                        QLineEdit {
                            padding: 8px;
                            border: 1px solid #dcdfe6;
                            border-radius: 4px;
                        }
                        QLineEdit:focus {
                            border-color: #409eff;
                        }
                    """)
                    form_layout.addRow('申请人姓名:', self.applicant_name)
                
                    # 组织/单位
                    self.organization = QLineEdit()
                    self.organization.setPlaceholderText('请输入组织或单位名称')
                    self.organization.setStyleSheet("""
                        QLineEdit {
                            padding: 8px;
                            border: 1px solid #dcdfe6;
                            border-radius: 4px;
                        }
                        QLineEdit:focus {
                            border-color: #409eff;
                        }
                    """)
                    form_layout.addRow('组织/单位:', self.organization)
                    
                    # 部门
                    self.department = QLineEdit()
                    self.department.setPlaceholderText('请输入部门名称（可选）')
                    self.department.setStyleSheet("""
                        QLineEdit {
                            padding: 8px;
                            border: 1px solid #dcdfe6;
                            border-radius: 4px;
                        }
                        QLineEdit:focus {
                            border-color: #409eff;
                        }
                    """)
                    form_layout.addRow('部门:', self.department)
                    
                    # 电子邮件
                    self.email = QLineEdit()
                    self.email.setPlaceholderText('请输入电子邮件地址')
                    self.email.setStyleSheet("""
                        QLineEdit {
                            padding: 8px;
                            border: 1px solid #dcdfe6;
                            border-radius: 4px;
                        }
                        QLineEdit:focus {
                            border-color: #409eff;
                        }
                    """)
                    form_layout.addRow('电子邮件:', self.email)
                
                    # 证书用途
                    self.usage_combo = QComboBox()
                    usages = ['数字签名', '身份认证', '数据加密', '代码签名', '其他']
                    for usage in usages:
                        self.usage_combo.addItem(usage)
                    self.usage_combo.setStyleSheet("""
                        QComboBox {
                            padding: 8px;
                            border: 1px solid #dcdfe6;
                            border-radius: 4px;
                        }
                        QComboBox:focus {
                            border-color: #409eff;
                        }
                    """)
                    form_layout.addRow('证书用途:', self.usage_combo)
                    
                    # 其他用途说明（当选择"其他"时显示）
                    self.other_usage = QLineEdit()
                    self.other_usage.setPlaceholderText('请说明其他用途')
                    self.other_usage.setStyleSheet("""
                        QLineEdit {
                            padding: 8px;
                            border: 1px solid #dcdfe6;
                            border-radius: 4px;
                        }
                        QLineEdit:focus {
                            border-color: #409eff;
                        }
                    """)
                    self.other_usage.setVisible(False)
                    form_layout.addRow('其他用途说明:', self.other_usage)
                    
                    # 连接用途选择变化信号
                    self.usage_combo.currentTextChanged.connect(self.on_usage_changed)
                    
                    # 备注
                    self.remarks = QTextEdit()
                    self.remarks.setPlaceholderText('请输入申请备注（可选）')
                    self.remarks.setStyleSheet("""
                        QTextEdit {
                            padding: 8px;
                            border: 1px solid #dcdfe6;
                            border-radius: 4px;
                            min-height: 80px;
                        }
                        QTextEdit:focus {
                            border-color: #409eff;
                        }
                    """)
                    form_layout.addRow('备注:', self.remarks)
                    
                    # 设置表单布局到组
                    form_group.setLayout(form_layout)
                    main_layout.addWidget(form_group)
                    
                    # 按钮布局
                    button_layout = QHBoxLayout()
                    button_layout.setSpacing(15)
                    
                    # 提交按钮
                    self.submit_btn = QPushButton('提交申请')
                    self.submit_btn.setStyleSheet("""
                        QPushButton {
                            padding: 8px 16px;
                            background-color: #409eff;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            min-width: 100px;
                        }
                        QPushButton:hover {
                            background-color: #66b1ff;
                        }
                        QPushButton:pressed {
                            background-color: #3a8ee6;
                        }
                    """)
                    self.submit_btn.clicked.connect(self.submit_application)
                    
                    # 取消按钮
                    self.cancel_btn = QPushButton('取消')
                    self.cancel_btn.setStyleSheet("""
                        QPushButton {
                            padding: 8px 16px;
                            background-color: #f56c6c;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            min-width: 100px;
                        }
                        QPushButton:hover {
                            background-color: #f78989;
                        }
                        QPushButton:pressed {
                            background-color: #dd6161;
                        }
                    """)
                    self.cancel_btn.clicked.connect(self.reject)
                    
                    button_layout.addStretch()
                    button_layout.addWidget(self.submit_btn)
                    button_layout.addWidget(self.cancel_btn)
                    
                    main_layout.addLayout(button_layout)
                    self.setLayout(main_layout)
                
                def on_usage_changed(self, text):
                    # 当选择"其他"
                    self.other_usage.setVisible(text == '其他')
                
                def submit_application(self):
                    # 验证必填字段
                    if not self.template_id:
                        QMessageBox.warning(self, '警告', '请选择证书模板')
                        return
                    
                    if not self.applicant_name.text().strip():
                        QMessageBox.warning(self, '警告', '请输入申请人姓名')
                        return
                    
                    if not self.organization.text().strip():
                        QMessageBox.warning(self, '警告', '请输入组织或单位名称')
                        return
                    
                    if not self.email.text().strip():
                        QMessageBox.warning(self, '警告', '请输入电子邮件地址')
                        return
                    
                    # 如果选择了其他用途但没有填写说明
                    if self.usage_combo.currentText() == '其他' and not self.other_usage.text().strip():
                        QMessageBox.warning(self, '警告', '请说明其他用途')
                        return
                    
                    # 收集表单数据
                    usage = self.usage_combo.currentText()
                    if usage == '其他':
                        usage = self.other_usage.text().strip()
                    
                    # 构建申请数据
                    application_data = {
                        'template_id': self.template_id,
                        'applicant_name': self.applicant_name.text().strip(),
                        'organization': self.organization.text().strip(),
                        'department': self.department.text().strip(),
                        'email': self.email.text().strip(),
                        'usage': usage,
                        'remarks': self.remarks.toPlainText().strip()
                    }
                    
                    # 调用父窗口的方法提交申请
                    if self.parent and hasattr(self.parent, 'submit_certificate_application'):
                        self.parent.submit_certificate_application(application_data)
                        self.accept()
                    else:
                        QMessageBox.critical(self, '错误', '无法提交证书申请，父窗口未实现相应方法')
        
            # 返回创建的对话框实例
            return CertificateApplicationDialog(self, template_id, template_name)
        except Exception as e:
            QMessageBox.critical(self, '错误', f'发送证书申请失败: {str(e)}')
            return None


    def set_key_save_path(self):
        """设置密钥保存路径"""
        try:
            # 打开文件夹选择对话框
            directory = QFileDialog.getExistingDirectory(self, '选择密钥保存目录', self.key_save_dir)
            if directory:  # 如果用户选择了目录
                self.key_save_dir = directory
                QMessageBox.information(self, '成功', f'密钥保存路径已设置为：\n{self.key_save_dir}')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'设置密钥保存路径失败: {str(e)}')


    async def verify_certificate(self):
        """验证证书"""
        try:
            # 获取证书序列号
            serial_number = self.verify_serial_input.text().strip()
            if not serial_number:
                QMessageBox.warning(self, '警告', '请输入证书序列号')
                return
            
            # 清空结果显示
            self.verify_result.clear()
            self.verify_result.setText("正在验证证书...")
            
            # 发送验证请求
            response = await asyncio.to_thread(self.client.send_request, 'verify_certificate', {
                'serial_number': serial_number
            })
            
            # 处理响应
            if response and response.get('status') == 'success':
                cert_data = response.get('data', {})
                
                # 格式化证书信息
                status = cert_data.get('status', '未知')
                status_text = {
                    'valid': '有效',
                    'revoked': '已撤销',
                    'expired': '已过期',
                    'pending': '待审核',
                    'approved':'已批准'
                }.get(status, '未知')
                
                # 构建结果文本
                result_text = f"证书验证结果:\n\n"
                result_text += f"序列号: {cert_data.get('serial_number', '未知')}\n"
                result_text += f"主题名称: {cert_data.get('subject_name', '未知')}\n"
                result_text += f"状态: {status_text}\n"
                result_text += f"颁发日期: {cert_data.get('issue_date', '未知')}\n"
                result_text += f"过期日期: {cert_data.get('expiry_date', '未知')}\n"
                
                # 根据状态添加不同的提示
                if status == 'valid':
                    result_text += "\n该证书有效，可以安全使用。"
                elif status == 'revoked':
                    result_text += "\n警告：该证书已被撤销，不应继续使用！"
                elif status == 'expired':
                    result_text += "\n警告：该证书已过期，不应继续使用！"
                elif status == 'pending':
                    result_text += "\n该证书正在审核中，尚未生效。"
                elif status == 'approved':
                    result_text += "\n该证书已批准，可以使用"
                
                # 显示结果
                self.verify_result.setText(result_text)
                
                # 如果证书有效，启用下载按钮
                if status == 'valid':
                    # 可以添加下载证书的提示
                    self.verify_result.append("\n\n您可以点击'下载证书'按钮获取此证书。")
            else:
                error_msg = response.get('message', '验证证书失败') if response else '验证证书失败，请稍后重试'
                self.verify_result.setText(f"验证失败: {error_msg}")
        except Exception as e:
            QMessageBox.critical(self, '错误', f'验证证书失败: {str(e)}')
            self.verify_result.setText(f"验证过程发生错误: {str(e)}")


class ChangePasswordDialog(QDialog):
    """修改密码对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle('修改密码')
        self.setFixedSize(400, 300)

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # 当前密码
        current_password_layout = QHBoxLayout()
        current_password_label = QLabel('当前密码')
        self.current_password_input = QLineEdit()
        self.current_password_input.setEchoMode(QLineEdit.Password)
        self.current_password_input.setPlaceholderText('请输入当前密码')
        current_password_layout.addWidget(current_password_label)
        current_password_layout.addWidget(self.current_password_input)
        layout.addLayout(current_password_layout)

        # 新密码
        new_password_layout = QHBoxLayout()
        new_password_label = QLabel('新密码')
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.Password)
        self.new_password_input.setPlaceholderText('请输入新密码')
        new_password_layout.addWidget(new_password_label)
        new_password_layout.addWidget(self.new_password_input)
        layout.addLayout(new_password_layout)

        # 确认新密码
        confirm_password_layout = QHBoxLayout()
        confirm_password_label = QLabel('确认新密码')
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input.setPlaceholderText('请再次输入新密码')
        confirm_password_layout.addWidget(confirm_password_label)
        confirm_password_layout.addWidget(self.confirm_password_input)
        layout.addLayout(confirm_password_layout)

        # 确认按钮
        button_layout = QHBoxLayout()
        self.confirm_btn = QPushButton('确认修改')
        self.confirm_btn.clicked.connect(self.change_password)
        self.cancel_btn = QPushButton('取消')
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.confirm_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def change_password(self):
        current_password = self.current_password_input.text()
        new_password = self.new_password_input.text()
        confirm_password = self.confirm_password_input.text()
        
        if not all([current_password, new_password, confirm_password]):
            QMessageBox.warning(self, '警告', '请填写所有密码字段')
            return
        
        if new_password != confirm_password:
            QMessageBox.warning(self, '警告', '两次输入的新密码不一致')
            return
        
        try:
            # 获取用户ID，如果parent有user_info属性
            user_id = None
            if hasattr(self.parent, 'user_info') and self.parent.user_info:
                user_id = self.parent.user_info.get('id')
            
            # 发送修改密码请求
            response = self.parent.client.send_request('change_password', {
                'current_password': current_password,
                'new_password': new_password,
                'user_id': user_id
            })
            
            if response and response.get('status') == 'success':
                QMessageBox.information(self, '成功', '密码修改成功')
                self.accept()
            else:
                error_msg = response.get('message', '密码修改失败') if response else '密码修改失败，请稍后重试'
                QMessageBox.warning(self, '失败', error_msg)
        except Exception as e:
            QMessageBox.critical(self, '错误', f'修改密码时发生错误: {str(e)}')