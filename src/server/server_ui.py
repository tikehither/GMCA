import logging
from datetime import datetime
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, \
    QPushButton, QLabel, QTextEdit, QTabWidget, QGroupBox, QFormLayout, QMessageBox, QLineEdit, QComboBox, QHeaderView, \
    QDialog, QSpinBox, QFileDialog, QCheckBox
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QMutex
from server import CAServer
import asyncio
import threading
import sys
import io
import mysql.connector
from secure_logger import secure_logger_manager

# 创建自定义日志处理器
class QTextEditLogger(logging.Handler):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s'))

    def emit(self, record):
        msg = self.format(record)
        self.widget.append(msg)
        # 同时记录到secure_logger
        secure_logger_manager.log(msg)


# 创建标准输出重定向类
class StdoutRedirector(io.StringIO):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget

    def write(self, text):
        if text.strip():  # 只输出非空内容
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.widget.append(f'[{timestamp}] {text.strip()}')

    def flush(self):
        pass


# 证书模板创建对话框
class TemplateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()
        
    def init_ui(self):
        # 设置窗口标题和大小
        self.setWindowTitle('创建证书模板')
        self.setFixedSize(500, 400)
        
        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建表单布局
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(15)
        form_layout.setHorizontalSpacing(20)
        
        # 模板名称
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText('请输入模板名称')
        self.name_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
            }
            QLineEdit:focus {
                border-color: #409eff;
            }
        """)
        form_layout.addRow('模板名称:', self.name_input)
        
        # 有效期（天）
        self.validity_input = QSpinBox()
        self.validity_input.setRange(1, 3650)  # 1天到10年
        self.validity_input.setValue(365)  # 默认1年
        self.validity_input.setStyleSheet("""
            QSpinBox {
                padding: 8px;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
            }
            QSpinBox:focus {
                border-color: #409eff;
            }
        """)
        form_layout.addRow('有效期(天):', self.validity_input)
        
        # 密钥用途
        self.key_usage_combo = QComboBox()
        key_usages = ['数字签名', '密钥加密', '数据加密', '证书签名', '全部']
        for usage in key_usages:
            self.key_usage_combo.addItem(usage)
        self.key_usage_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
            }
            QComboBox:focus {
                border-color: #409eff;
            }
        """)
        form_layout.addRow('密钥用途:', self.key_usage_combo)
        
        # 角色权限选择
        self.roles_group = QGroupBox("角色权限")
        roles_layout = QVBoxLayout()
        
        self.admin_checkbox = QCheckBox("管理员")
        self.admin_checkbox.setChecked(True)  # 默认选中
        self.admin_checkbox.setStyleSheet("""
            QCheckBox {
                padding: 5px;
            }
            QCheckBox:hover {
                color: #409eff;
            }
        """)
        
        self.user_checkbox = QCheckBox("普通用户")
        self.user_checkbox.setChecked(True)  # 默认选中
        self.user_checkbox.setStyleSheet("""
            QCheckBox {
                padding: 5px;
            }
            QCheckBox:hover {
                color: #409eff;
            }
        """)
        
        roles_layout.addWidget(self.admin_checkbox)
        roles_layout.addWidget(self.user_checkbox)
        self.roles_group.setLayout(roles_layout)
        form_layout.addRow('可用角色:', self.roles_group)
        
        # 添加表单到主布局
        main_layout.addLayout(form_layout)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        # 保存按钮
        self.save_btn = QPushButton('保存')
        self.save_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #409eff;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #66b1ff;
            }
            QPushButton:pressed {
                background-color: #3a8ee6;
            }
        """)
        self.save_btn.clicked.connect(self.save_template)
        
        # 取消按钮
        self.cancel_btn = QPushButton('取消')
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #f56c6c;
                color: white;
                border: none;
                border-radius: 4px;
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
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
    
    def save_template(self):
        # 获取表单数据
        name = self.name_input.text().strip()
        validity_period = self.validity_input.value()
        key_usage = self.key_usage_combo.currentText()
        
        # 获取角色权限
        allowed_roles = []
        if self.admin_checkbox.isChecked():
            allowed_roles.append('admin')
        if self.user_checkbox.isChecked():
            allowed_roles.append('user')
            
        # 验证数据
        if not name:
            QMessageBox.warning(self, '警告', '请输入模板名称')
            return
            
        if not allowed_roles:
            QMessageBox.warning(self, '警告', '请至少选择一个可用角色')
            return
        
        # 创建模板数据
        template_data = {
            'name': name,
            'validity_period': validity_period,
            'key_usage': key_usage,
            'allowed_roles': ','.join(allowed_roles)
        }
        
        # 调用父窗口的创建模板方法
        if self.parent and hasattr(self.parent, 'create_certificate_template'):
            self.parent.create_certificate_template(template_data)
            self.accept()
        else:
            QMessageBox.critical(self, '错误', '无法创建证书模板，父窗口未实现相应方法')


class ServerThread(QThread):
    error_signal = pyqtSignal(str)  # 错误信号
    _stop_signal = pyqtSignal()  # 停止信号
    reload_signal = pyqtSignal()  # 重载信号
    log_signal = pyqtSignal(str)  # 添加日志信号

    def __init__(self, server):
        super().__init__()
        try:
            self.server = server
            self.loop = None
            self._is_running = True
            self.mutex = QMutex()
            self._stop_signal.connect(self._async_stop, Qt.DirectConnection)
            self.reload_signal.connect(self._async_reload, Qt.QueuedConnection)

            # 初始化日志系统
            self.log("服务器线程初始化完成")
        except Exception as e:
            self.error_signal.emit(f"服务器线程初始化失败: {str(e)}")
            raise

    def log(self, message):
        """发送日志信息"""
        self.log_signal.emit(message)

    def run(self):
        """运行服务器线程"""
        try:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.stop()
                    loop.close()
            except RuntimeError:
                pass

            # 创建新的事件循环
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            # 创建异步关闭钩子
            self.loop.set_exception_handler(self._handle_async_exception)

            # 启动服务器
            try:
                # 设置更长的超时时间
                self.loop.slow_callback_duration = 2.0
                # 创建启动任务
                start_task = self.loop.create_task(self.server.start())
                # 运行事件循环直到服务器启动完成
                self.loop.run_until_complete(start_task)
                self.log("服务器进入事件循环")
                self.log("服务器启动成功！")
                # 继续运行事件循环
                self.loop.run_forever()
            except asyncio.CancelledError:
                self.log("服务器启动被取消")
                return

        except Exception as e:
            self.log(f"服务器线程运行错误: {str(e)}")
            import traceback
            self.log(f"错误详情:\n{traceback.format_exc()}")
            self.error_signal.emit(f"服务器线程运行错误: {str(e)}")
        finally:
            self.cleanup()
            self.log("服务器线程已完全停止")

    def cleanup(self):
        """清理资源"""
        try:
            self.log("开始清理服务器资源...")
            if self.loop and not self.loop.is_closed():
                self.log("停止事件循环...")
                try:
                    # 先停止事件循环
                    if self.loop.is_running():
                        self.loop.stop()

                    # 取消所有未完成的任务
                    current_task = asyncio.current_task(loop=self.loop)
                    pending = [t for t in asyncio.all_tasks(self.loop) 
                              if t is not current_task and not t.done()]
                    if pending:
                        self.log(f"正在取消 {len(pending)} 个未完成的任务...")
                        for task in pending:
                            task.cancel()

                        # 等待任务完成，设置较短的超时时间
                        try:
                            self.loop.run_until_complete(
                                asyncio.wait(pending, timeout=3.0)
                            )
                        except (asyncio.TimeoutError, RuntimeError):
                            self.log("部分任务未能在超时时间内完成")

                    # 关闭事件循环
                    self.loop.close()
                    self.log("事件循环已关闭")
                except Exception as e:
                    self.log(f"停止事件循环时出错: {str(e)}")
            else:
                self.log("事件循环已经关闭或不存在")
        except Exception as e:
            self.log(f"清理资源时发生错误: {str(e)}")
        finally:
            self.log("资源清理完成")

    def stop(self):
        """线程安全停止方法"""
        self.log("开始停止服务器线程")
        if self.loop and self.loop.is_running():
            try:
                # 先取消所有任务，确保没有任务会阻止事件循环停止
                for task in asyncio.all_tasks(self.loop):
                    if not task.done() and not task.cancelled():
                        task.cancel()
                
                # 在当前事件循环中执行异步停止
                future = asyncio.run_coroutine_threadsafe(self._async_stop(), self.loop)
                
                try:
                    # 等待异步停止操作完成，设置超时
                    future.result(timeout=5.0)
                except asyncio.TimeoutError:
                    self.log("停止操作超时，继续进行强制停止流程")
                except asyncio.CancelledError:
                    self.log("停止操作被取消，继续进行强制停止流程")
                except Exception as e:
                    self.log(f"停止操作异常: {str(e)}，继续进行强制停止流程")
                
                # 确保事件循环停止
                if self.loop.is_running():
                    self.log("强制停止事件循环")
                    self.loop.call_soon_threadsafe(self.loop.stop)

            except Exception as e:
                self.log(f"停止操作发生严重异常: {str(e)}")
                # 即使发生异常也要尝试停止事件循环
                if self.loop and self.loop.is_running():
                    self.loop.call_soon_threadsafe(self.loop.stop)

    async def _async_stop(self):
        """异步关闭流程"""
        self.log("开始异步停止流程")
        try:
            # 1. 停止接受新连接
            if hasattr(self.server, 'close'):
                await self.server.close()

            # 2. 取消所有任务，但排除当前任务
            current_task = asyncio.current_task()
            tasks = [t for t in asyncio.all_tasks(self.loop) if t is not current_task and not t.done()]
            if tasks:
                self.log(f"正在取消 {len(tasks)} 个未完成的任务...")
                for task in tasks:
                    task.cancel()
                try:
                    await asyncio.wait(tasks, timeout=5.0)
                except asyncio.TimeoutError:
                    self.log("部分任务未能在超时时间内完成")
                except Exception as e:
                    self.log(f"等待任务完成时发生错误: {str(e)}")

            # 3. 停止事件循环
            if self.loop and self.loop.is_running():
                self.loop.call_soon_threadsafe(self.loop.stop)
                self.log("事件循环已安全停止")

        except Exception as e:
            self.log(f"停止失败: {str(e)}")
            self.error_signal.emit(f"停止失败: {str(e)}")
            # 不再抛出异常，避免中断停止流程
            # 即使发生异常也要尝试停止事件循环
            if self.loop and self.loop.is_running():
                self.loop.call_soon_threadsafe(self.loop.stop)

    def _handle_async_exception(self, loop, context):
        """捕获异步循环内部异常"""
        error_msg = context.get('exception', context['message'])
        self.log(f"异步错误: {error_msg}")
        
        # 检查是否是客户端断开连接的异常，如果是则不做特殊处理
        exception = context.get('exception')
        if isinstance(exception, (ConnectionResetError, ConnectionError, OSError)):
            self.log("客户端连接异常，服务器将继续运行")
            return
        
        # 记录完整上下文信息（仅对非客户端连接异常）
        self.log(f"完整上下文: {context}")
        self.error_signal.emit(f"服务器错误: {error_msg}")
            
        # 其他严重异常可能需要特殊处理
        if isinstance(exception, SystemExit):
            self.log("收到系统退出信号，服务器将安全停止")
            asyncio.create_task(self._async_stop())
        

    async def _async_reload(self):
        """异步重载配置"""
        try:
            if hasattr(self.server, 'reload_config'):
                await self.server.reload_config()
        except Exception as e:
            self.error_signal.emit(str(e))

class AddUserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle('添加用户')
        self.resize(400, 200)
        
        # 创建布局
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        # 用户名输入框
        self.username_input = QLineEdit()
        form_layout.addRow('用户名:', self.username_input)
        
        # 密码输入框
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow('密码:', self.password_input)
        
        # 确认密码输入框
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow('确认密码:', self.confirm_password_input)
        
        # 角色选择下拉框
        self.role_combo = QComboBox()
        self.role_combo.addItems(['普通用户', '管理员'])
        form_layout.addRow('角色:', self.role_combo)
        
        layout.addLayout(form_layout)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton('确定')
        self.cancel_button = QPushButton('取消')
        
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
    def get_user_data(self):
        """获取用户输入的数据"""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        role = 'admin' if self.role_combo.currentText() == '管理员' else 'user'
        
        # 验证输入
        if not username:
            QMessageBox.warning(self, '警告', '用户名不能为空')
            return None
            
        if not password:
            QMessageBox.warning(self, '警告', '密码不能为空')
            return None
            
        if password != confirm_password:
            QMessageBox.warning(self, '警告', '两次输入的密码不一致')
            return None
            
        return {
            'username': username,
            'password': password,
            'role': role
        }

class ServerUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.server = None
        self.server_thread = None
        self.full_logs = []  # 存储完整的日志记录

        # 设置窗口属性
        self.setWindowTitle('CA服务器管理界面')
        self.setGeometry(100, 100, 1000, 800)

        # 初始化UI组件
        self.init_ui()
        self.init_timer()

        # 初始化状态变量
        self.connected_clients = 0
        self.is_running = False

        # 设置窗口显示
        self.show()
        self.raise_()
        self.activateWindow()

        # 初始化日志系统
        from secure_logger import secure_logger_manager
        secure_logger_manager.ui_callback = self.append_log
        
        # 使用与刷新按钮相同的日志加载逻辑
        import os
        config = secure_logger_manager.load_config()
        # 检查配置中是否存在logging键
        if 'logging' in config:
            log_file = os.path.join(secure_logger_manager.log_dir, config['logging']['file'])
        else:
            # 如果没有找到logging键，使用默认的server.log
            log_file = os.path.join(secure_logger_manager.log_dir, 'server.log')
            self.append_log("警告: 配置中未找到'logging'键，使用默认日志文件'server.log'")
        try:
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_content = f.read()
                    self.full_logs = [line for line in log_content.split('\n') if line.strip()]  # 更新完整日志列表
                    self.log_text.clear()
                    self.log_text.append(log_content)
            else:
                self.append_log(f"警告: 日志文件 {log_file} 不存在")
                self.full_logs = []
        except Exception as e:
            self.append_log(f"加载日志失败: {str(e)}")
            self.full_logs = []

        self.append_log("服务器UI初始化完成")

    def init_ui(self):
        self.setWindowTitle('CA服务器管理界面')
        self.setGeometry(100, 100, 1000, 800)

        # 设置窗口居中显示
        screen = QApplication.primaryScreen().geometry()
        window_geometry = self.geometry()
        x = (screen.width() - window_geometry.width()) // 2
        y = (screen.height() - window_geometry.height()) // 2
        self.move(x, y)

        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 左侧面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # 服务器状态组
        status_group = QGroupBox('服务器状态')
        status_layout = QFormLayout()
        self.status_label = QLabel('运行中')
        self.clients_label = QLabel('0')
        status_layout.addRow('状态:', self.status_label)
        status_layout.addRow('连接数:', self.clients_label)
        status_group.setLayout(status_layout)
        left_layout.addWidget(status_group)

        # 控制按钮组
        control_group = QGroupBox('控制面板')
        control_layout = QVBoxLayout()
        self.start_btn = QPushButton('启动服务器')
        self.stop_btn = QPushButton('停止服务器')
        self.reload_btn = QPushButton('重载配置')
        self.start_btn.clicked.connect(self.start_server)
        self.stop_btn.clicked.connect(self.stop_server)
        self.reload_btn.clicked.connect(self.reload_config)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.reload_btn)
        control_group.setLayout(control_layout)
        left_layout.addWidget(control_group)

        main_layout.addWidget(left_panel)

        # 右侧标签页
        tabs = QTabWidget()

        # 日志标签页
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        
        # 日志工具栏
        log_toolbar = QHBoxLayout()
        
        # 日志类型过滤
        self.log_type_combo = QComboBox()
        self.log_type_combo.addItems(['全部', '证书操作', '用户认证', '系统事件'])
        self.log_type_combo.currentTextChanged.connect(self.filter_logs)
        log_toolbar.addWidget(QLabel('日志类型:'))
        log_toolbar.addWidget(self.log_type_combo)
        
        # 日志搜索
        self.log_search = QLineEdit()
        self.log_search.setPlaceholderText('搜索日志...')
        self.log_search.textChanged.connect(self.filter_logs)
        log_toolbar.addWidget(self.log_search)
        
        # 刷新按钮
        self.refresh_log_btn = QPushButton('刷新日志')
        self.refresh_log_btn.clicked.connect(self.refresh_logs)
        log_toolbar.addWidget(self.refresh_log_btn)
        
        # 导出按钮
        self.export_log_btn = QPushButton('导出日志')
        self.export_log_btn.clicked.connect(self.export_logs)
        log_toolbar.addWidget(self.export_log_btn)
        
        # 清空按钮
        self.clear_log_btn = QPushButton('清空日志')
        self.clear_log_btn.clicked.connect(self.clear_logs)
        log_toolbar.addWidget(self.clear_log_btn)
        
        log_layout.addLayout(log_toolbar)
        
        # 日志显示区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        tabs.addTab(log_tab, '系统日志')

        # 证书管理标签页
        cert_tab = QWidget()
        cert_layout = QVBoxLayout(cert_tab)

        # 证书列表
        cert_list_group = QGroupBox('证书列表')
        cert_list_layout = QVBoxLayout()

        # 添加刷新按钮
        refresh_cert_btn = QPushButton('刷新证书列表')
        refresh_cert_btn.setStyleSheet("""
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
        refresh_cert_btn.clicked.connect(self.load_certificates)
        cert_list_layout.addWidget(refresh_cert_btn, alignment=Qt.AlignRight)

        # 创建证书表格
        self.cert_table = QTableWidget()
        self.cert_table.setColumnCount(9)
        self.cert_table.setHorizontalHeaderLabels(['序列号', '公钥', '申请者', '状态', '申请时间', '签发时间', '到期时间', '用途', '操作'])
        self.cert_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        cert_list_layout.addWidget(self.cert_table)

        # 证书操作按钮组
        cert_btn_layout = QHBoxLayout()
        self.approve_cert_btn = QPushButton('审核通过')
        self.reject_cert_btn = QPushButton('拒绝申请')
        self.revoke_cert_btn = QPushButton('吊销证书')
        self.export_cert_btn = QPushButton('导出证书')
        self.create_template_btn = QPushButton('创建模板')

        # 连接按钮事件
        self.approve_cert_btn.clicked.connect(self.approve_certificate)
        self.reject_cert_btn.clicked.connect(self.reject_certificate)
        self.revoke_cert_btn.clicked.connect(self.revoke_certificate)
        self.export_cert_btn.clicked.connect(self.export_certificate)
        self.create_template_btn.clicked.connect(self.open_template_dialog)

        cert_btn_layout.addWidget(self.approve_cert_btn)
        cert_btn_layout.addWidget(self.reject_cert_btn)
        cert_btn_layout.addWidget(self.revoke_cert_btn)
        cert_btn_layout.addWidget(self.export_cert_btn)
        cert_btn_layout.addWidget(self.create_template_btn)
        cert_list_layout.addLayout(cert_btn_layout)

        # 注释掉重复的连接，这是导致弹窗出现两次的原因
        # self.create_template_btn.clicked.connect(self.open_template_dialog)

        cert_list_group.setLayout(cert_list_layout)
        cert_layout.addWidget(cert_list_group)
        tabs.addTab(cert_tab, '证书管理')

        # 用户管理标签页
        user_tab = QWidget()
        user_layout = QVBoxLayout(user_tab)

        # 用户列表
        user_list_group = QGroupBox('用户列表')
        user_list_layout = QVBoxLayout()

        # 创建用户表格
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(6)
        self.user_table.setHorizontalHeaderLabels(['用户名', '角色', '注册时间', '最后登录', '状态', '操作'])
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        user_list_layout.addWidget(self.user_table)

        # 用户操作按钮组
        user_btn_layout = QHBoxLayout()
        self.add_user_btn = QPushButton('添加用户')
        self.refresh_user_btn = QPushButton('刷新列表')

        # 连接按钮事件
        self.add_user_btn.clicked.connect(self.show_add_user_dialog)
        self.refresh_user_btn.clicked.connect(self.load_users)

        user_btn_layout.addWidget(self.add_user_btn)
        user_btn_layout.addWidget(self.refresh_user_btn)
        user_list_layout.addLayout(user_btn_layout)

        user_list_group.setLayout(user_list_layout)
        user_layout.addWidget(user_list_group)
        tabs.addTab(user_tab, '用户管理')

        # 系统配置标签页
        config_tab = QWidget()
        config_layout = QVBoxLayout(config_tab)

        # 服务器配置组
        server_group = QGroupBox('服务器配置')
        server_form = QFormLayout()
        self.server_host = QLineEdit()
        self.server_port = QLineEdit()
        self.server_max_conn = QLineEdit()
        server_form.addRow('主机:', self.server_host)
        server_form.addRow('端口:', self.server_port)
        server_form.addRow('最大连接数:', self.server_max_conn)
        server_group.setLayout(server_form)
        config_layout.addWidget(server_group)

        # 数据库配置组
        db_group = QGroupBox('数据库配置')
        db_form = QFormLayout()
        self.db_type = QLineEdit()
        self.db_path = QLineEdit()
        db_form.addRow('数据库类型:', self.db_type)
        db_form.addRow('数据库路径:', self.db_path)
        db_group.setLayout(db_form)
        config_layout.addWidget(db_group)

        # 日志配置组
        log_group = QGroupBox('日志配置')
        log_form = QFormLayout()
        self.log_level = QLineEdit()
        self.log_file = QLineEdit()
        self.log_max_size = QLineEdit()
        self.log_backup_count = QLineEdit()
        log_form.addRow('日志级别:', self.log_level)
        log_form.addRow('日志文件:', self.log_file)
        log_form.addRow('最大大小(字节):', self.log_max_size)
        log_form.addRow('备份数量:', self.log_backup_count)
        log_group.setLayout(log_form)
        config_layout.addWidget(log_group)

        # 安全配置组
        security_group = QGroupBox('安全配置')
        security_form = QFormLayout()
        self.security_key_size = QLineEdit()
        self.security_cert_validity = QLineEdit()
        self.security_session_timeout = QLineEdit()
        self.security_max_attempts = QLineEdit()
        self.security_lockout_duration = QLineEdit()
        security_form.addRow('密钥大小:', self.security_key_size)
        security_form.addRow('证书有效期(天):', self.security_cert_validity)
        security_form.addRow('会话超时(秒):', self.security_session_timeout)
        security_form.addRow('最大失败尝试:', self.security_max_attempts)
        security_form.addRow('锁定时间(秒):', self.security_lockout_duration)
        security_group.setLayout(security_form)
        config_layout.addWidget(security_group)

        # 保存按钮
        save_btn = QPushButton('保存配置')
        save_btn.clicked.connect(self.save_config)
        config_layout.addWidget(save_btn)

        config_tab.setLayout(config_layout)
        tabs.addTab(config_tab, '系统配置')

        main_layout.addWidget(tabs)
        main_layout.setStretch(0, 1)  # 左侧面板占比
        main_layout.setStretch(1, 4)  # 右侧标签页占比

        # 加载配置
        self.load_config()

    def init_timer(self):
        """初始化定时器，用于更新界面状态"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(1000)  # 每秒更新一次
        
    def filter_logs(self):
        """根据类型和搜索关键词过滤日志"""
        log_type = self.log_type_combo.currentText()
        search_text = self.log_search.text().lower()
        
        filtered_logs = []
        
        # 从完整日志列表中筛选
        for log in self.full_logs:
            # 根据日志类型过滤
            if log_type != '全部':
                if log_type == '证书操作' and not any(x in log.lower() for x in ['证书', '签发', '撤销']):
                    continue
                elif log_type == '用户认证' and not any(x in log.lower() for x in ['登录', '认证', '用户']):
                    continue
                elif log_type == '系统事件' and not any(x in log.lower() for x in ['系统', '服务器', '配置']):
                    continue
            
            # 根据搜索文本过滤
            if search_text and search_text not in log.lower():
                continue
                
            filtered_logs.append(log)
        
        # 更新日志显示
        self.log_text.clear()
        if filtered_logs:
            self.log_text.append('\n'.join(filtered_logs))

    def refresh_logs(self):
        """刷新日志显示，重置过滤条件并显示所有日志"""
        # 重置过滤条件
        self.log_type_combo.setCurrentText('全部')
        self.log_search.clear()
        
        # 从日志文件重新加载日志内容
        from secure_logger import secure_logger_manager
        import os
        log_file = os.path.join(secure_logger_manager.log_dir, secure_logger_manager.load_config()['logging']['file'])
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
                self.full_logs = [line for line in log_content.split('\n') if line.strip()]  # 更新完整日志列表
                self.log_text.clear()
                self.log_text.append(log_content)
        except Exception as e:
            self.append_log(f"刷新日志失败: {str(e)}")
    
    def export_logs(self):
        """导出日志到文件"""
        try:
            # 获取保存文件路径
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                '导出日志',
                '',
                'Log Files (*.log);;Text Files (*.txt);;All Files (*)'
            )
            
            if file_path:
                # 写入日志内容
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                QMessageBox.information(self, '成功', '日志导出成功！')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'导出日志失败：{str(e)}')
    
    def clear_logs(self):
        """清空日志显示"""
        reply = QMessageBox.question(
            self,
            '确认',
            '确定要清空所有日志吗？',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.full_logs = []  # 清空完整日志列表
            self.log_text.clear()

    def load_certificates(self):
        """加载证书列表"""
        try:
            if not self.server or not hasattr(self.server, 'db'):
                self.append_log("服务器未启动，无法加载证书列表")
                return
            
            # 清空表格
            self.cert_table.setRowCount(0)
        
            # 从数据库获取证书列表和证书申请列表
            conn = self.server.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            try:
                # 获取已签发的证书（certificates表）
                try:
                    cursor.execute("""
                        SELECT 
                            serial_number, 
                            public_key, 
                            subject_name, 
                            status, 
                            NULL AS submit_date,  -- 证书没有申请时间
                            issue_date, 
                            expiry_date, 
                            template_id
                        FROM certificates
                        WHERE status IN ('valid', 'revoked')
                        ORDER BY issue_date DESC
                    """)
                    certificates = cursor.fetchall()
                except mysql.connector.Error as err:
                    self.append_log(f"查询证书表失败: {err}")
                    certificates = []
            
                # 获取待审核的证书申请（certificate_applications表）
                try:
                    cursor.execute("""
                        SELECT 
                            serial_number, 
                            public_key, 
                            subject_name, 
                            organization,
                            status, 
                            submit_date,
                            NULL AS issue_date,  -- 申请没有签发时间
                            NULL AS expiry_date, -- 申请没有到期时间
                            `usage` AS usage_purpose,
                            template_id
                        FROM certificate_applications
                        WHERE status = 'pending'
                        ORDER BY submit_date DESC
                    """)
                    applications = cursor.fetchall()
                except mysql.connector.Error as err:
                    self.append_log(f"查询证书申请表失败: {err}")
                    applications = []
                
                # 合并证书列表
                all_certificates = certificates + applications
                
                if not all_certificates:
                    self.append_log("没有找到任何证书记录")
                    return
            
                # 填充表格
                for i, cert in enumerate(all_certificates):
                    self.cert_table.insertRow(i)
                
                    # 序列号
                    self.cert_table.setItem(i, 0, QTableWidgetItem(cert['serial_number']))
                    
                    # 公钥（截断显示）
                    public_key = cert.get('public_key', '-')
                    if len(public_key) > 30:
                        public_key = public_key[:30] + '...'
                    self.cert_table.setItem(i, 1, QTableWidgetItem(public_key))
                
                    # 申请者（从subject_name解析CN）
                    subject_name = cert.get('subject_name', '-')
                    try:
                        # 解析subject_name中的CN
                        if "CN=" in subject_name:
                            applicant = subject_name.split("CN=")[1].split(",")[0]
                        else:
                            applicant = subject_name
                    except Exception:
                        applicant = subject_name
                
                    # 附加组织信息（仅申请记录有organization字段）
                    organization = cert.get('organization', '')
                    if organization:
                        applicant += f" ({organization})"
                    self.cert_table.setItem(i, 2, QTableWidgetItem(applicant))
                
                    # 状态显示
                    status = cert.get('status', 'unknown')
                    status_text = {
                        'pending': '待审核',
                        'valid': '有效',
                        'revoked': '已撤销',
                        'approved': '已批准',  # 申请可能的状态
                        'rejected': '已拒绝'
                    }.get(status, '未知')
                
                    status_item = QTableWidgetItem(status_text)
                    # 根据状态设置背景色
                    if status == 'pending':
                        status_item.setBackground(Qt.yellow)
                    elif status == 'valid':
                        status_item.setBackground(Qt.green)
                    elif status in ('revoked', 'rejected'):
                        status_item.setBackground(Qt.red)
                    else:
                        status_item.setBackground(Qt.white)
                    self.cert_table.setItem(i, 3, status_item)
                
                    # 申请时间（仅申请记录有submit_date）
                    submit_date = cert.get('submit_date')
                    submit_display = submit_date.strftime('%Y-%m-%d %H:%M:%S') if submit_date else '-'
                    self.cert_table.setItem(i, 4, QTableWidgetItem(submit_display))
                
                    # 签发时间（仅证书记录有issue_date）
                    issue_date = cert.get('issue_date')
                    issue_display = issue_date.strftime('%Y-%m-%d %H:%M:%S') if issue_date else '-'
                    self.cert_table.setItem(i, 5, QTableWidgetItem(issue_display))
                
                    # 到期时间（仅证书记录有expiry_date）
                    expiry_date = cert.get('expiry_date')
                    expiry_display = expiry_date.strftime('%Y-%m-%d %H:%M:%S') if expiry_date else '-'
                    self.cert_table.setItem(i, 6, QTableWidgetItem(expiry_display))
                
                    # 用途处理逻辑
                    usage = '-'
                    template_id = cert.get('template_id')
                
                    # 如果是申请记录，优先使用自身的usage字段
                    if 'usage_purpose' in cert and cert['usage_purpose']:
                        usage = cert['usage_purpose']
                    # 如果未填写或无效，尝试从模板获取
                    if usage == '-' and template_id:
                        try:
                            template = self.server.db.get_certificate_template(template_id)
                            if template:
                                usage = template.get('key_usage', '-')
                        except Exception as e:
                            self.append_log(f"获取模板{template_id}用途失败: {str(e)}")
                
                    self.cert_table.setItem(i, 7, QTableWidgetItem(usage))
                
                    # 操作按钮文本
                    if status == 'pending':
                        btn_text = "审核"
                    elif status == 'valid':
                        btn_text = "吊销"
                    else:
                        btn_text = "详情"
                    self.cert_table.setItem(i, 8, QTableWidgetItem(btn_text))
            
                self.append_log(f"已加载 {len(all_certificates)} 条证书记录")
            except Exception as db_err:
                self.append_log(f"加载证书列表失败: {str(db_err)}")
                import traceback
                self.append_log(traceback.format_exc())
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            self.append_log(f"加载证书列表时发生错误: {str(e)}")
    
    def approve_certificate(self):
        """审核通过证书"""
        try:
            # 获取选中的行
            selected_rows = self.cert_table.selectedItems()
            if not selected_rows:
                QMessageBox.warning(self, '警告', '请先选择要审核的证书')
                return
                
            # 获取证书序列号
            row = selected_rows[0].row()
            serial_number = self.cert_table.item(row, 0).text()
            status_text = self.cert_table.item(row, 3).text()
            
            # 检查证书状态
            if status_text != '待审核':
                QMessageBox.warning(self, '警告', '只能审核状态为待审核的证书')
                return
                
            # 确认操作
            reply = QMessageBox.question(self, '确认', f'确定要审核通过证书 {serial_number} 吗？',
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
                
            # 先进行心跳检测
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            #try:
            #    # 检查客户端是否在线
            #    client_alive = loop.run_until_complete(
            #        self.server.check_client_alive(serial_number)
            #    )
                
            #    if not client_alive:
            #        QMessageBox.warning(self, '警告', '客户端不在线，请等待客户端上线后再尝试审核')
            #        return
                
            # 客户端在线，继续审核流程
            result = loop.run_until_complete(
                self.server.handle_certificate_approval({'serial_number': serial_number})
            )
                
            if result and result.get('status') == 'success':
                QMessageBox.information(self, '成功', '证书审核已通过')
                self.append_log(f"已审核通过证书 {serial_number}")
                # 刷新证书列表
                self.load_certificates()
            else:
                error_msg = result.get('message', '操作失败') if result else '操作失败'
                QMessageBox.warning(self, '失败', error_msg)
            #finally:
            #    loop.close()
        except Exception as e:
            QMessageBox.critical(self, '错误', f'审核证书时发生错误: {str(e)}')
    
    def reject_certificate(self):
        """拒绝证书申请"""
        try:
            # 获取选中的行
            selected_rows = self.cert_table.selectedItems()
            if not selected_rows:
                QMessageBox.warning(self, '警告', '请先选择要拒绝的证书申请')
                return
                
            # 获取证书序列号
            row = selected_rows[0].row()
            serial_number = self.cert_table.item(row, 0).text()
            status_text = self.cert_table.item(row, 3).text()
            
            # 检查证书状态
            if status_text != '待审核':
                QMessageBox.warning(self, '警告', '只能拒绝状态为待审核的证书申请')
                return
                
            # 确认操作
            reply = QMessageBox.question(self, '确认', f'确定要拒绝证书申请 {serial_number} 吗？',
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
                
            # 调用服务器方法拒绝证书申请
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    self.server.handle_certificate_rejection({'serial_number': serial_number})
                )
                
                if result and result.get('status') == 'success':
                    QMessageBox.information(self, '成功', '证书申请已拒绝')
                    # 刷新证书列表
                    self.load_certificates()
                else:
                    error_msg = result.get('message', '操作失败') if result else '操作失败'
                    QMessageBox.warning(self, '失败', error_msg)
            finally:
                loop.close()
        except Exception as e:
            QMessageBox.critical(self, '错误', f'拒绝证书申请时发生错误: {str(e)}')
    
    def revoke_certificate(self):
        """吊销证书"""
        try:
            # 获取选中的行
            selected_rows = self.cert_table.selectedItems()
            if not selected_rows:
                QMessageBox.warning(self, '警告', '请先选择要吊销的证书')
                return
                
            # 获取证书序列号
            row = selected_rows[0].row()
            serial_number = self.cert_table.item(row, 0).text()
            status_text = self.cert_table.item(row, 3).text()
            
            # 检查证书状态
            if status_text != '有效':
                QMessageBox.warning(self, '警告', '只能吊销状态为有效的证书')
                return
                
            # 确认操作
            reply = QMessageBox.question(self, '确认', f'确定要吊销证书 {serial_number} 吗？\n吊销后将无法恢复！',
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
                
            # 调用服务器方法吊销证书
            if self.server and hasattr(self.server, 'db'):
                result = self.server.db.revoke_certificate(serial_number)
                
                if result:
                    QMessageBox.information(self, '成功', '证书已成功吊销')
                    # 刷新证书列表
                    self.load_certificates()
                    self.append_log(f'证书 {serial_number} 已被吊销')
                else:
                    QMessageBox.warning(self, '失败', '吊销证书失败，请检查日志获取详细信息')
            else:
                QMessageBox.warning(self, '错误', '服务器未启动或数据库连接失败')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'吊销证书时发生错误: {str(e)}')
            self.append_log(f'吊销证书时发生错误: {str(e)}')
            
    def export_certificate(self):
        """导出证书"""
        try:
            # 获取选中的行
            selected_rows = self.cert_table.selectedItems()
            if not selected_rows:
                QMessageBox.warning(self, '警告', '请先选择要导出的证书')
                return
                
            # 获取证书序列号
            row = selected_rows[0].row()
            serial_number = self.cert_table.item(row, 0).text()
            status_text = self.cert_table.item(row, 3).text()
            
            # 检查证书状态
            if status_text != '有效':
                QMessageBox.warning(self, '警告', '只能导出状态为有效的证书')
                return
                
            # 选择保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                '导出证书',
                f'certificate_{serial_number}.pem',
                '证书文件 (*.pem);;所有文件 (*)'
            )
            
            if not file_path:
                return  # 用户取消了操作
                
            # 调用服务器方法导出证书
            if self.server and hasattr(self.server, 'db'):
                try:
                    # 获取证书内容
                    cert_data = self.server.db.get_certificate_data(serial_number)
                    
                    if not cert_data:
                        QMessageBox.warning(self, '失败', '无法获取证书数据')
                        return
                        
                    # 写入文件
                    with open(file_path, 'w') as f:
                        f.write(cert_data)
                        
                    QMessageBox.information(self, '成功', f'证书已成功导出到: {file_path}')
                    self.append_log(f'证书 {serial_number} 已导出到 {file_path}')
                except Exception as export_err:
                    QMessageBox.warning(self, '失败', f'导出证书失败: {str(export_err)}')
                    self.append_log(f'导出证书失败: {str(export_err)}')
            else:
                QMessageBox.warning(self, '错误', '服务器未启动或数据库连接失败')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'导出证书时发生错误: {str(e)}')
            self.append_log(f'导出证书时发生错误: {str(e)}')
            
    def update_status(self):
        """更新服务器状态显示"""
        # 从服务器实例获取当前连接数
        if self.server and self.is_running and hasattr(self.server, 'get_active_connections'):
            self.connected_clients = self.server.get_active_connections()
            
        self.clients_label.setText(str(self.connected_clients))

    def append_log(self, message):
        """添加日志到显示区域"""
        # 检查消息是否已包含时间戳，如果没有则添加
        if not message.startswith('[20'):
            from datetime import datetime
            timestamp = datetime.now().strftime('[%Y-%m-%d %H:%M:%S]')
            if 'ERROR' in message.upper():
                level = 'ERROR'
            elif 'WARNING' in message.upper():
                level = 'WARNING'
            else:
                level = 'INFO'
            message = f"{timestamp} {level}: {message}"

        self.full_logs.append(message)  # 添加到完整日志列表
        self.log_text.append(message)  # 添加到显示区域
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def load_users(self):
        """加载用户列表"""
        try:
            if not self.server or not hasattr(self.server, 'db'):
                self.append_log("服务器未启动，无法加载用户列表")
                return

            # 清空表格
            self.user_table.setRowCount(0)

            # 从数据库获取用户列表
            users = self.server.db.list_users()

            # 填充表格
            for i, user in enumerate(users):
                self.user_table.insertRow(i)

                # 用户名
                self.user_table.setItem(i, 0, QTableWidgetItem(user['username']))

                # 角色
                role_text = '管理员' if user['role'] == 'admin' else '普通用户'
                self.user_table.setItem(i, 1, QTableWidgetItem(role_text))

                # 注册时间
                created_at = user['created_at'].strftime('%Y-%m-%d %H:%M:%S') if user['created_at'] else '未知'
                self.user_table.setItem(i, 2, QTableWidgetItem(created_at))

                # 最后登录（暂无此数据）
                self.user_table.setItem(i, 3, QTableWidgetItem('--'))

                # 状态（暂无此数据）
                self.user_table.setItem(i, 4, QTableWidgetItem('正常'))

                # 操作按钮
                delete_btn = QPushButton('删除')
                delete_btn.setProperty('user_id', user['id'])
                delete_btn.clicked.connect(self.delete_user)
                self.user_table.setCellWidget(i, 5, delete_btn)

            self.append_log(f"已加载 {len(users)} 个用户")
        except Exception as e:
            self.append_log(f"加载用户列表时发生错误: {str(e)}")
    def show_add_user_dialog(self):
        """显示添加用户对话框"""
        try:
            # 检查服务器是否运行
            if not self.server or not hasattr(self.server, 'db'):
                QMessageBox.warning(self, '警告', '服务器未启动，无法添加用户')
                return
                
            
            # 创建并显示对话框
            dialog = AddUserDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                user_data = dialog.get_user_data()
                if user_data:
                    self.add_user(user_data)
        except Exception as e:
            self.append_log(f"显示添加用户对话框时发生错误: {str(e)}")
            QMessageBox.critical(self, '错误', f'显示添加用户对话框失败: {str(e)}')
    
    def add_user(self, user_data):
        """添加用户"""
        try:
            self.append_log(f"开始添加用户: {user_data['username']}")
            
            # 创建异步任务
            async def add_user_task():
                result = await self.server.handle_user_registration(user_data)
                return result
            
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(add_user_task())
                
                if result.get('status') == 'success':
                    self.append_log(f"用户 {user_data['username']} 添加成功")
                    QMessageBox.information(self, '成功', f'用户 {user_data["username"]} 添加成功')
                    # 刷新用户列表
                    self.load_users()
                else:
                    error_msg = result.get('message', '未知错误')
                    self.append_log(f"用户添加失败: {error_msg}")
                    QMessageBox.critical(self, '错误', f'用户添加失败: {error_msg}')
            finally:
                loop.close()
        except Exception as e:
            self.append_log(f"添加用户时发生错误: {str(e)}")
            QMessageBox.critical(self, '错误', f'添加用户失败: {str(e)}')
    
    def delete_user(self):
        """删除用户"""
        try:
            # 获取发送信号的按钮
            sender = self.sender()
            if not sender:
                return
                
            # 获取用户ID
            user_id = sender.property('user_id')
            if not user_id:
                QMessageBox.warning(self, '警告', '无法获取用户ID')
                return
                
            # 确认删除
            reply = QMessageBox.question(self, '确认删除', '确定要删除该用户吗？此操作不可撤销！',
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
                
            # 创建异步任务
            async def delete_user_task():
                result = await self.server.handle_user_deletion({'user_id': user_id})
                return result
            
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(delete_user_task())
                
                if result.get('status') == 'success':
                    self.append_log(f"用户(ID:{user_id})删除成功")
                    QMessageBox.information(self, '成功', '用户删除成功')
                    # 刷新用户列表
                    self.load_users()
                else:
                    error_msg = result.get('message', '未知错误')
                    self.append_log(f"用户删除失败: {error_msg}")
                    QMessageBox.critical(self, '错误', f'用户删除失败: {error_msg}')
            finally:
                loop.close()
        except Exception as e:
            self.append_log(f"删除用户时发生错误: {str(e)}")
            QMessageBox.critical(self, '错误', f'删除用户失败: {str(e)}')


    def start_server(self):
        """启动服务器"""
        try:
            if self.server is not None:
                self.append_log("服务器已在运行中")
                return

            self.append_log("正在启动服务器...")
            self.server = CAServer()
            self.server_thread = ServerThread(self.server)
            self.server_thread.log_signal.connect(self.append_log)
            self.server_thread.error_signal.connect(self.handle_server_error)
            self.server_thread.start()

            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.status_label.setText('运行中')
            self.is_running = True

            # 加载证书和用户列表
            self.load_certificates()
            self.load_users()

            self.append_log("服务器启动成功")
        except Exception as e:
            self.append_log(f"启动服务器失败: {str(e)}")
            self.server = None
            self.server_thread = None

    def stop_server(self):
        if self.is_running and self.server_thread:
            try:
                self.append_log('开始安全停止服务器...')

                # 使用stop方法而不是直接发送信号
                # 这样可以确保_async_stop协程被正确等待
                self.server_thread.stop()

                # 等待线程结束，设置较短的超时时间
                if not self.server_thread.wait(5000):  # 等待5秒
                    self.append_log("等待线程结束超时，进行强制终止")
                    self.server_thread.terminate()

                # 清理资源
                self._cleanup_resources()

            except Exception as e:
                self.append_log(f'停止异常: {str(e)}')
                import traceback
                self.append_log(f'错误详情:\n{traceback.format_exc()}')
            finally:
                self.is_running = False
                self._update_ui_state(False)

    def _cleanup_resources(self):
        """安全清理资源"""
        try:
            if self.server_thread:
                self.server_thread.deleteLater()
                self.server_thread = None

            if self.server:
                del self.server
                self.server = None

            # 强制GC
            import gc
            gc.collect()
            self.append_log("资源清理完成")
        except Exception as e:
            self.append_log(f"清理资源时出错: {str(e)}")

    def _update_ui_state(self, running):
        """线程安全更新UI状态"""
        self.status_label.setText('运行中' if running else '已停止')
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)

    def handle_server_stopped(self):
        """处理服务器停止"""
        self.is_running = False
        self._update_ui_state(False)
        self.append_log('服务器已停止')

    def handle_server_error(self, error_msg):
        """处理服务器错误"""
        self.append_log(f'服务器错误: {error_msg}')
        QMessageBox.critical(self, '服务器错误', error_msg)
        self.stop_server()  # 发生错误时自动停止服务器

    def save_config(self):
        try:
            import yaml
            import os
            
            # 读取原始配置文件，保留注释和格式
            with open('config.yaml', 'r', encoding='utf-8') as f:
                original_config = yaml.safe_load(f)
            
            # 从UI获取新的配置值
            new_config = {
                'server': {
                    'host': self.server_host.text(),
                    'port': int(self.server_port.text()),
                    'max_connections': int(self.server_max_conn.text())
                },
                'database': {
                    'type': self.db_type.text(),
                    # 保留原有的数据库配置项
                    'host': original_config.get('database', {}).get('host', 'localhost'),
                    'port': original_config.get('database', {}).get('port', 3306),
                    'database': original_config.get('database', {}).get('database', 'ca_system'),
                    'user': original_config.get('database', {}).get('user', 'your_db_user'),
                    'password': original_config.get('database', {}).get('password', 'your_db_password'),
                    'pool_size': original_config.get('database', {}).get('pool_size', 5),
                    'pool_name': original_config.get('database', {}).get('pool_name', 'mypool'),
                    'connect_timeout': original_config.get('database', {}).get('connect_timeout', 30),
                    'retry_count': original_config.get('database', {}).get('retry_count', 5),
                    'retry_delay': original_config.get('database', {}).get('retry_delay', 3)
                },
                'logging': {
                    'level': self.log_level.text(),
                    'file': self.log_file.text(),
                    'max_size': int(self.log_max_size.text()),
                    'backup_count': int(self.log_backup_count.text()),
                    'format': original_config.get('logging', {}).get('format', '[%(asctime)s] %(levelname)s: %(message)s')
                },
                'security': {
                    'key_size': int(self.security_key_size.text()),
                    'cert_validity_days': int(self.security_cert_validity.text()),
                    'session_timeout': int(self.security_session_timeout.text()),
                    'max_failed_attempts': int(self.security_max_attempts.text()),
                    'lockout_duration': int(self.security_lockout_duration.text())
                }
            }
            
            # 创建备份文件
            if os.path.exists('config.yaml'):
                backup_path = 'config.yaml.bak'
                with open('config.yaml', 'r', encoding='utf-8') as src, open(backup_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
                self.append_log(f'已创建配置文件备份: {backup_path}')
            
            # 写入新配置，保持格式
            with open('config.yaml', 'w', encoding='utf-8') as f:
                # 添加文件头注释
                f.write("# CA服务器配置文件\n\n")
                
                # 服务器配置
                f.write("# 服务器配置\n")
                yaml.dump({'server': new_config['server']}, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
                f.write("\n")
                
                # 数据库配置
                f.write("# 数据库配置\n")
                yaml.dump({'database': new_config['database']}, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
                f.write("\n")
                
                # 日志配置
                f.write("# 日志配置\n")
                yaml.dump({'logging': new_config['logging']}, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
                f.write("\n")
                
                # 安全配置
                f.write("# 安全配置\n")
                yaml.dump({'security': new_config['security']}, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            self.append_log('配置保存成功')
            QMessageBox.information(self, '成功', '配置已保存')
        except ValueError as e:
            QMessageBox.critical(self, '错误', '请确保所有数值类型的配置项填写正确')
            self.append_log(f'保存配置失败：数值类型错误 - {str(e)}')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'保存配置失败：{str(e)}')
            self.append_log(f'保存配置失败：{str(e)}')

    def load_config(self):
        try:
            import yaml
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # 加载服务器配置
            server_config = config.get('server', {})
            self.server_host.setText(str(server_config.get('host', '')))
            self.server_port.setText(str(server_config.get('port', '')))
            self.server_max_conn.setText(str(server_config.get('max_connections', '')))

            # 加载数据库配置
            db_config = config.get('database', {})
            self.db_type.setText(str(db_config.get('type', '')))
            # 注意：这里的db_path可能需要根据实际UI组件进行调整
            # 如果UI中有对应的数据库主机、端口、用户名、密码等字段，应该在这里加载
            if hasattr(self, 'db_host'):
                self.db_host.setText(str(db_config.get('host', '')))
            if hasattr(self, 'db_port'):
                self.db_port.setText(str(db_config.get('port', '')))
            if hasattr(self, 'db_name'):
                self.db_name.setText(str(db_config.get('database', '')))
            if hasattr(self, 'db_user'):
                self.db_user.setText(str(db_config.get('user', '')))
            if hasattr(self, 'db_password'):
                self.db_password.setText(str(db_config.get('password', '')))
            # 确保db_path仍然被设置，以保持向后兼容性
            if hasattr(self, 'db_path'):
                self.db_path.setText(str(db_config.get('path', '')))

            # 加载日志配置
            log_config = config.get('logging', {})
            self.log_level.setText(str(log_config.get('level', '')))
            self.log_file.setText(str(log_config.get('file', '')))
            self.log_max_size.setText(str(log_config.get('max_size', '')))
            self.log_backup_count.setText(str(log_config.get('backup_count', '')))

            # 加载安全配置
            security_config = config.get('security', {})
            self.security_key_size.setText(str(security_config.get('key_size', '')))
            self.security_cert_validity.setText(str(security_config.get('cert_validity_days', '')))
            self.security_session_timeout.setText(str(security_config.get('session_timeout', '')))
            self.security_max_attempts.setText(str(security_config.get('max_failed_attempts', '')))
            self.security_lockout_duration.setText(str(security_config.get('lockout_duration', '')))

            self.append_log('配置加载成功')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'加载配置失败：{str(e)}')
            self.append_log(f'加载配置失败：{str(e)}')

    def reload_config(self):
        """重新加载配置"""
        try:
            self.load_config()
            if self.server_thread and self.is_running:
                self.server_thread.reload_signal.emit()  # 通过信号触发重载
            self.append_log('配置重新加载成功')
            QMessageBox.information(self, '成功', '配置已重新加载')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'重新加载配置失败：{str(e)}')
            self.append_log(f'重新加载配置失败：{str(e)}')
            
    def open_template_dialog(self):
        """打开证书模板创建对话框"""
        try:
            template_dialog = TemplateDialog(self)
            template_dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, '错误', f'打开证书模板管理失败: {str(e)}')
    
    def create_certificate_template(self, template_data):
        """创建证书模板"""
        try:
            self.append_log(f"开始创建证书模板: {template_data['name']}")
            
            # 检查服务器是否运行
            if not self.server or not self.is_running:
                QMessageBox.warning(self, '警告', '服务器未运行，无法创建证书模板')
                return
            
            # 创建异步任务
            async def create_template():
                result = await self.server.handle_template_creation(template_data)
                return result
            
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(create_template())
                
                if result.get('status') == 'success':
                    template_id = result.get('data', {}).get('template_id')
                    self.append_log(f"证书模板创建成功，ID: {template_id}")
                    QMessageBox.information(self, '成功', f'证书模板 {template_data["name"]} 创建成功')
                else:
                    error_msg = result.get('message', '未知错误')
                    self.append_log(f"证书模板创建失败: {error_msg}")
                    QMessageBox.critical(self, '错误', f'证书模板创建失败: {error_msg}')
            finally:
                loop.close()
        except Exception as e:
            self.append_log(f"创建证书模板时发生错误: {str(e)}")
            QMessageBox.critical(self, '错误', f'创建证书模板失败: {str(e)}')


def main():
    try:
        # 使用已存在的QApplication实例或创建新的
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)
        server_ui = ServerUI()

        # 初始化日志系统
        from secure_logger import secure_logger_manager
        secure_logger_manager.ui_callback = server_ui.append_log

        # 显示并激活窗口
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

        # 设置全局异常处理器
        def global_exception_handler(exctype, value, traceback):
            error_msg = f"未捕获的异常: {exctype.__name__}: {str(value)}"
            if hasattr(server_ui, 'append_log'):
                server_ui.append_log(error_msg)
                server_ui.append_log("异常详细信息:")
                import traceback as tb
                for line in tb.format_tb(traceback):
                    server_ui.append_log(line.strip())
            print(error_msg, file=sys.stderr)
            sys.__excepthook__(exctype, value, traceback)  # 调用默认的异常处理器

        # 设置全局异常处理器
        sys.excepthook = global_exception_handler

        return server_ui
    except Exception as e:
        error_msg = f"程序启动失败: {str(e)}"
        print(error_msg, file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    main()


    
