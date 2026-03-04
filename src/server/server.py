import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from crypto_gmssl import GMSCrypto
from database import DatabaseManager
from secure_logger import secure_logger_manager
from typing import Optional, Dict

import constants
import os
class CAServer:
    def __init__(self, host='0.0.0.0', port=8888, log_callback=None):
        self.host = host
        self.port = port
        self.log_callback = log_callback
        self.crypto = GMSCrypto()
        self.db = DatabaseManager(log_callback=log_callback)
        self.server = None
        # 添加连接计数器
        self.active_connections = 0
        # 添加客户端连接映射表
        self.client_connections = {}
        # 添加证书序列号到客户端连接的映射
        self.cert_client_map = {}
        # 初始化日志模块
        self.logger = secure_logger_manager
        
        print(f"CA服务器初始化完成，监听地址: {host}:{port}")
        
        # 检查并生成根证书
        if not self.crypto.is_root_certificate_exists():
            self.log("正在生成CA根证书...")
            if self.crypto.generate_root_certificate():
                self.log("CA根证书生成成功")
                print("CA根证书生成成功")
            else:
                self.log("CA根证书生成失败，请检查配置")

        # 设置日志回调
        if log_callback:
            secure_logger_manager.ui_callback = log_callback

    
            
    def get_active_connections(self):
        """获取当前活跃连接数"""
        return self.active_connections

    def log(self, message):
        """统一的日志处理"""
        secure_logger_manager.get_logger().info(message)

    async def handle_client(self, reader, writer):
        """处理客户端连接"""
        addr = writer.get_extra_info('peername')
        addr_str = 'Unknown' if addr is None else f'{addr[0]}:{addr[1]}'
        self.log(f'客户端连接: {addr_str}')
        
        # 增加连接计数
        self.active_connections += 1
        self.log(f'当前连接数: {self.active_connections}')
        print(f"当前连接数: {self.active_connections}")
        
        # 保存客户端连接信息
        self.client_connections[addr_str] = (reader, writer)
        
        try:
            while True:
                # 接收数据
                try:
                    data = await reader.read(8192)
                    if not data:
                        self.log(f'客户端 {addr_str} 断开连接')
                        print(f"客户端 {addr_str} 断开连接")
                        break
                    
                    self.log(f'从 {addr_str} 接收到 {len(data)} 字节的数据')
                    
                    # 验证数据格式
                    try:
                        data_str = data.decode().strip()
                        request = json.loads(data_str)
                        
                        if not isinstance(request, dict):
                            response = {'status': 'error', 'message': '无效的请求格式'}
                        elif 'action' not in request or 'data' not in request:
                            response = {'status': 'error', 'message': '请求缺少必要字段'}
                        else:
                            # 处理请求，传递客户端地址用于安全日志
                            response = await self.handle_request(request, addr_str)
                            
                        # 发送响应
                        try:
                            response_str = json.dumps(response)
                            writer.write(response_str.encode())
                            await writer.drain()
                        except (ConnectionResetError, ConnectionError, OSError, BrokenPipeError) as e:
                            self.log(f'向客户端 {addr_str} 发送响应时连接断开: {str(e)}')
                            break
                        
                    except UnicodeDecodeError:
                        try:
                            response = {'status': 'error', 'message': '数据解码失败'}
                            writer.write(json.dumps(response).encode())
                            await writer.drain()
                        except (ConnectionResetError, ConnectionError, OSError, BrokenPipeError):
                            self.log(f'向客户端 {addr_str} 发送错误响应时连接断开')
                            break
                    except json.JSONDecodeError:
                        try:
                            response = {'status': 'error', 'message': '无效的JSON格式'}
                            writer.write(json.dumps(response).encode())
                            await writer.drain()
                        except (ConnectionResetError, ConnectionError, OSError, BrokenPipeError):
                            self.log(f'向客户端 {addr_str} 发送错误响应时连接断开')
                            break
                    except Exception as e:
                        try:
                            response = {'status': 'error', 'message': f'处理请求时发生错误: {str(e)}'}
                            writer.write(json.dumps(response).encode())
                            await writer.drain()
                        except (ConnectionResetError, ConnectionError, OSError, BrokenPipeError):
                            self.log(f'向客户端 {addr_str} 发送错误响应时连接断开')
                            break
                        
                except (ConnectionResetError, ConnectionError, OSError, BrokenPipeError) as e:
                    self.log(f'客户端 {addr_str} 断开连接: {str(e)}')
                    break
                except Exception as e:
                    self.log(f'接收客户端 {addr_str} 数据时发生未预期的错误: {str(e)}')
                    break
                    
        except Exception as e:
            self.log(f'处理客户端 {addr_str} 连接时发生错误: {str(e)}')
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                self.log(f'关闭客户端 {addr_str} 连接时发生错误: {str(e)}')
            # 减少连接计数
            self.active_connections -= 1
            # 清理连接映射
            if addr_str in self.client_connections:
                del self.client_connections[addr_str]
            # 清理证书序列号映射
            for serial_number, client_addr in list(self.cert_client_map.items()):
                if client_addr == addr_str:
                    del self.cert_client_map[serial_number]
            self.log(f'客户端 {addr_str} 的连接已关闭，当前连接数: {self.active_connections}')

    async def close(self):
        """关闭服务器"""
        try:
            if self.server:
                # 先关闭服务器，停止接受新的连接
                self.server.close()
                await self.server.wait_closed()
                
                # 获取当前事件循环
                loop = asyncio.get_running_loop()
                
                # 取消所有正在运行的任务
                tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task()]
                if tasks:
                    self.log(f'正在等待 {len(tasks)} 个任务完成...')
                    # 取消所有任务
                    for task in tasks:
                        task.cancel()
                    # 等待所有任务完成，设置超时时间为5秒
                    try:
                        await asyncio.wait(tasks, timeout=5)
                    except asyncio.TimeoutError:
                        self.log('部分任务未能在超时时间内完成')
                    except Exception as e:
                        self.log(f'等待任务完成时发生错误: {str(e)}')
                
                self.log('服务器已关闭')
                print('服务器已完全关闭')
        except Exception as e:
            self.log(f'关闭服务器时发生错误: {str(e)}')
            raise

    async def start(self):
        """启动服务器"""
        try:
            self.log("开始创建服务器...")
            print("开始创建服务器...")
            self.server = await asyncio.start_server(
                self.handle_client,
                self.host,
                self.port
            )

            addr = self.server.sockets[0].getsockname()
            self.log(f'CA服务器启动在 {addr}')
            
            # 加载证书模板数量
            try:
                templates = self.db.list_certificate_templates()
                self.log(f'已加载 {len(templates)} 个证书模板')
                print(f'已加载 {len(templates)} 个证书模板')
            except Exception as e:
                self.log(f'加载证书模板失败: {str(e)}')
            
            self.log('服务器启动成功！')

            async with self.server:
                try:
                    await self.server.serve_forever()
                except asyncio.CancelledError:
                    self.log("服务器收到取消信号，开始优雅关闭...")
                    print("服务器收到取消信号，开始优雅关闭...")
                    # 等待所有连接处理完成
                    await self.close()
                    self.log("服务器已安全关闭")
                    print("服务器已安全关闭")
                    return
        except Exception as e:
            self.log(f'服务器启动失败: {str(e)}')
            raise

    def start_sync(self):
        """同步启动服务器"""
        try:
            # 确保在主线程中运行
            if asyncio._get_running_loop() is not None:
                raise RuntimeError("不能在已有事件循环的线程中调用start_sync")

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 设置异常处理器
            def exception_handler(loop, context):
                exception = context.get('exception')
                if exception:
                    self.log(f'发生未处理的异常: {str(exception)}')
                else:
                    self.log(f'发生错误: {context["message"]}')

            loop.set_exception_handler(exception_handler)

            try:
                # 初始化数据库连接
                loop.run_until_complete(self._init_async())
                print("数据库连接初始化完成")
                # 启动服务器
                loop.run_until_complete(self.start())
                loop.run_forever()
            except asyncio.CancelledError:
                self.log('服务器收到取消信号')
            except Exception as e:
                self.log(f'服务器运行错误: {str(e)}')
                raise
            finally:
                try:
                    # 关闭服务器并清理资源
                    loop.run_until_complete(self.close())
                    print("服务器资源已清理")
                    
                    # 确保所有任务都已完成
                    pending = asyncio.all_tasks(loop)
                    if pending:
                        loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True))
                    
                    # 关闭事件循环
                    loop.stop()
                    loop.close()
                except Exception as e:
                    self.log(f'清理资源时发生错误: {str(e)}')
        except Exception as e:
            self.log(f'启动服务器时发生严重错误: {str(e)}')
            raise

    async def _init_async(self):
        """异步初始化服务器资源"""
        try:
            # 这里可以添加其他异步初始化操作
            pass
        except Exception as e:
            self.log(f'初始化服务器资源失败: {str(e)}')
            raise

    async def handle_request(self, request, client_addr=None):
        """处理客户端请求，增加了客户端地址参数用于安全日志"""
        action = request['action']
        data = request['data']
        
        # 获取客户端地址（如果未提供）
        if client_addr is None:
            writer = data.get('_writer')
            if writer:
                addr = writer.get_extra_info('peername')
                client_addr = 'Unknown' if addr is None else f'{addr[0]}:{addr[1]}'
            else:
                client_addr = 'Unknown'
        
        # 直接处理请求，不再使用SM4加密
        try:
            # 设置请求处理超时
            timeout = 45.0  # 设置45秒的超时时间
            
            # 使用asyncio.wait_for来添加超时控制
            try:
                if action == 'register':
                    response = await asyncio.wait_for(self.handle_register(data, client_addr), timeout)
                elif action == 'login':
                    response = await asyncio.wait_for(self.handle_user_login(data, client_addr), timeout)
                elif action == 'get_user_info':
                    response = await asyncio.wait_for(self.handle_get_user_info(data), timeout)
                elif action == 'update_user_info':
                    response = await asyncio.wait_for(self.handle_update_user_info(data, client_addr), timeout)
                elif action == 'change_password':
                    response = await asyncio.wait_for(self.handle_change_password(data, client_addr), timeout)
                elif action == 'request_certificate':
                    response = await asyncio.wait_for(self.handle_certificate_request(data, client_addr), timeout)
                elif action == 'get_certificate_templates':
                    response = await asyncio.wait_for(self.handle_get_certificate_templates(data), timeout)
                elif action == 'get_certificate_applications':
                    response = await asyncio.wait_for(self.handle_get_certificate_applications(data), timeout)
                elif action == 'approve_certificate':
                    response = await asyncio.wait_for(self.handle_certificate_approval(data, client_addr), timeout)
                elif action == 'reject_certificate':
                    response = await asyncio.wait_for(self.handle_certificate_rejection(data, client_addr), timeout)
                elif action == 'verify_certificate':
                    response = await asyncio.wait_for(self.handle_certificate_verification(data), timeout)
                elif action == 'apply_certificate':
                    response = await asyncio.wait_for(self.handle_certificate_application(data, client_addr), timeout)
                elif action == 'download_certificate':
                    response = await asyncio.wait_for(self.handle_certificate_download(data), timeout)
                elif action == 'ping':
                    # 处理ping请求，用于测试服务器连接
                    response = {'status': 'success', 'message': 'pong', 'data': {'timestamp': time.time()}}
                else:
                    response = {'status': 'error', 'message': '未知的请求类型'}
                    print(f"未知的请求类型: {action}")
                    
            except asyncio.TimeoutError:
                self.log(f'处理请求 {action} 超时，已超过 {timeout} 秒')
                return {'status': 'error', 'message': f'请求处理超时，请稍后重试'}
                
            return response
        except Exception as e:
            self.log(f'处理请求 {action} 时发生错误: {str(e)}')
            import traceback
            import logging
            self.log('发生内部错误，详情已记录到日志')
            return {'status': 'error', 'message': '处理请求时发生错误，请稍后重试'}

    async def handle_get_certificate_applications(self, data):
        """处理获取证书申请记录请求（获取pending状态的证书）"""
        try:
            # 参数验证
            if not data or not isinstance(data, dict):
                return {'status': 'error', 'message': '无效的请求数据'}
            
            # 获取pending状态的证书记录（即待审核的证书申请）
            conn = self.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            try:
                # 获取所有pending证书记录
                cursor.execute("""
                    SELECT serial_number, subject_name, status, issue_date, expiry_date, usage_purpose, template_id
                    FROM certificates 
                    WHERE status = 'pending'
                    ORDER BY issue_date DESC
                """)
                
                certificates = cursor.fetchall()
            
                # 格式化证书记录
                formatted_certificates = []
                for cert in certificates:
                    formatted_cert = {
                        'serial_number': cert['serial_number'],
                        'subject_name': cert['subject_name'],
                        'status': cert['status'],
                        'submit_date': cert['issue_date'].isoformat() if cert['issue_date'] else None,
                        'issue_date': cert['issue_date'].isoformat() if cert['issue_date'] else None,
                        'expiry_date': cert['expiry_date'].isoformat() if cert['expiry_date'] else None,
                        'usage': cert.get('usage_purpose', ''),
                        'template_id': cert.get('template_id', '')
                    }
                    formatted_certificates.append(formatted_cert)
            
                self.log(f"获取待审核证书申请成功，共{len(formatted_certificates)}条记录")
                return {
                    'status': 'success',
                    'data': formatted_certificates
                }
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            self.log(f'获取证书申请记录失败: {e}')
            return {'status': 'error', 'message': f'获取证书申请记录失败: {str(e)}'}


    async def handle_get_certificate_templates(self, data):
        """处理获取证书模板列表请求"""
        try:
            # 获取用户ID（可选参数，用于筛选用户有权限使用的模板）
            user_id = data.get('user_id')
            
            # 获取所有证书模板
            templates = self.db.get_certificate_templates()
            
            if not templates:
                return {'status': 'success', 'data': {'templates': []}}
            
            # 如果提供了用户ID，筛选用户有权限使用的模板
            if user_id:
                authorized_templates = []
                for template in templates:
                    # 检查用户是否有权限使用该模板
                    has_permission = self.db.check_template_permission(template['id'], user_id)
                    # 管理员用户默认有所有模板的权限
                    # 先获取用户信息
                    user_info = self.db.get_user(user_id)
                    is_admin = user_info and user_info.get('role') == 'admin' if user_info else False
                    
                    if has_permission or is_admin:
                        # 添加权限标记
                        template['has_permission'] = True
                        authorized_templates.append(template)
                    else:
                        # 普通用户也可以看到没有权限的模板，但标记为无权限
                        template['has_permission'] = False
                        authorized_templates.append(template)
                
                templates = authorized_templates
            
            # 格式化模板数据
            formatted_templates = []
            for template in templates:
                formatted_template = {
                    'id': template['id'],
                    'name': template['name'],
                    'validity_period': template['validity_period'],
                    'key_usage': template['key_usage'],
                    'allowed_roles': template.get('allowed_roles', 'admin,user'),
                    'created_at': template['created_at'].isoformat() if 'created_at' in template else None,
                    'has_permission': template.get('has_permission', True)
                }
                formatted_templates.append(formatted_template)
            
            self.log(f"获取证书模板列表成功，共{len(formatted_templates)}个模板")
            return {
                'status': 'success',
                'data': {
                    'templates': formatted_templates
                }
            }
            
        except Exception as e:
            self.log(f'获取证书模板列表失败: {e}')
            return {'status': 'error', 'message': f'获取证书模板列表失败: {str(e)}'}

    async def handle_user_registration(self, data):
        """处理用户注册"""
        try:
            username = data.get('username')
            password = data.get('password')
            role = data.get('role', 'user')

            # 使用SM3进行密码哈希
            password_hash = self.crypto.sm3_hash(password)

            # 保存用户信息
            success = self.db.add_user(username, password_hash, role)

            if success:
                return {'status': 'success', 'message': '用户注册成功'}
            else:
                return {'status': 'error', 'message': '用户注册失败'}

        except Exception as e:
            logging.error(f'处理用户注册错误: {e}')
            return {'status': 'error', 'message': str(e)}
            
    async def handle_user_deletion(self, data):
        """处理用户删除"""
        try:
            user_id = data.get('user_id')
            
            if not user_id:
                return {'status': 'error', 'message': '用户ID不能为空'}
                
            # 删除用户
            success = self.db.delete_user(user_id)
            
            if success:
                return {'status': 'success', 'message': '用户删除成功'}
            else:
                return {'status': 'error', 'message': '用户删除失败'}
                
        except Exception as e:
            logging.error(f'处理用户删除错误: {e}')
            return {'status': 'error', 'message': str(e)}

    async def handle_user_login(self, data, client_addr=None):
        """处理用户登录请求，增加安全日志记录"""
        try:
            # 验证输入数据
            username = data.get('username')
            password_hash = data.get('password')  # 客户端已经发送了密码的SM3哈希值
            
            if not username or not password_hash:
                return {'status': 'error', 'message': '用户名或密码不能为空'}
            
            self.log(f'收到登录请求: 用户名={username}')
        
            # 验证用户
            user = self.db.verify_user(username, password_hash)
            if not user:
                # 记录失败登录事件
                self.logger.log_admin_event(username, '登录', {'ip_address': client_addr, 'result': 'failed'})
                return {'status': 'error', 'message': '用户名或密码错误'}
            
            # 记录成功登录事件
            self.logger.log_admin_event(username, '登录', {'ip_address': client_addr, 'result': 'success'})
            
            # 读取服务器公钥
            server_public_key = None
            try:
                with open(self.crypto.sm2_public_key, 'r') as f:
                    server_public_key = f.read()
                self.log(f'已读取服务器公钥，长度: {len(server_public_key)} 字节')
            except Exception as e:
                self.log(f'读取服务器公钥失败: {str(e)}')
            
            # 构建响应
            response_data = {
                'user_id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'server_public_key': server_public_key
            }
        
            return {
                'status': 'success',
                'data': response_data
            }
            
        except Exception as e:
            self.log(f'用户登录失败: {str(e)}')
            return {'status': 'error', 'message': str(e)}

    async def handle_establish_session(self, data):
        """处理建立会话请求"""
        try:
            user_id = data.get('user_id')
            encrypted_session_key = data.get('session_key')
        
            if not user_id or not encrypted_session_key:
                return {'status': 'error', 'message': '缺少必要参数', 'action': 'establish_session'}
            
            # 验证用户是否存在
            user = self.db.get_user_by_id(user_id)
            if not user:
                return {'status': 'error', 'message': '用户不存在', 'action': 'establish_session'}
            
            # 创建会话
            if not hasattr(self, 'session_manager'):
                return {'status': 'error', 'message': '会话管理器未初始化', 'action': 'establish_session'}
            
            success = self.session_manager.create_session(user_id, encrypted_session_key)
            if not success:
                return {'status': 'error', 'message': '创建会话失败', 'action': 'establish_session'}
            
            self.log(f"用户 {user['username']} 的会话已建立")
        
            return {
                'status': 'success',
                'message': '会话建立成功',
                'action': 'establish_session',
                'data': {
                    'user_id': user_id,
                    'username': user['username']
                }
            }
        except Exception as e:
            self.log(f"建立会话失败: {str(e)}")
            import traceback
            import logging
            traceback.print_exc()
            return {'status': 'error', 'message': '建立会话失败，请稍后重试', 'action': 'establish_session'}


    async def handle_user_update(self, data):
        """处理用户信息更新"""
        try:
            user_id = data.get('user_id')
            password = data.get('password')
            role = data.get('role')

            # 如果提供了新密码，使用SM3进行哈希
            password_hash = self.crypto.sm3_hash(password) if password else None

            # 更新用户信息
            success = self.db.update_user(user_id, password_hash, role)

            if success:
                return {'status': 'success', 'message': '用户信息更新成功'}
            else:
                return {'status': 'error', 'message': '用户信息更新失败'}

        except Exception as e:
            logging.error(f'处理用户信息更新错误: {e}')
            return {'status': 'error', 'message': str(e)}

    async def handle_template_creation(self, data):
        """处理证书模板创建"""
        try:
            name = data.get('name')
            validity_period = data.get('validity_period')
            key_usage = data.get('key_usage')
            allowed_roles = data.get('allowed_roles', 'admin,user')

            # 创建证书模板
            template_id = self.db.create_certificate_template(name, validity_period, key_usage, allowed_roles)

            if template_id:
                return {
                    'status': 'success',
                    'data': {
                        'template_id': template_id,
                        'name': name,
                        'allowed_roles': allowed_roles
                    }
                }
            else:
                return {'status': 'error', 'message': '证书模板创建失败'}

        except Exception as e:
            logging.error(f'处理证书模板创建错误: {e}')
            return {'status': 'error', 'message': str(e)}

    async def handle_template_update(self, data):
        """处理证书模板更新"""
        try:
            template_id = data.get('template_id')
            name = data.get('name')
            validity_period = data.get('validity_period')
            key_usage = data.get('key_usage')
            allowed_roles = data.get('allowed_roles')

            # 更新证书模板
            success = self.db.update_certificate_template(
                template_id,
                name=name,
                validity_period=validity_period,
                key_usage=key_usage,
                allowed_roles=allowed_roles
            )

            if success:
                return {'status': 'success', 'message': '证书模板更新成功'}
            else:
                return {'status': 'error', 'message': '证书模板更新失败'}

        except Exception as e:
            logging.error(f'处理证书模板更新错误: {e}')
            return {'status': 'error', 'message': str(e)}

    async def handle_template_permission(self, data):
        """处理证书模板权限设置"""
        try:
            template_id = data.get('template_id')
            user_id = data.get('user_id')
            can_use = data.get('can_use', True)

            # 设置模板权限
            success = self.db.set_template_permission(template_id, user_id, can_use)

            if success:
                return {'status': 'success', 'message': '证书模板权限设置成功'}
            else:
                return {'status': 'error', 'message': '证书模板权限设置失败'}

        except Exception as e:
            logging.error(f'处理证书模板权限设置错误: {e}')
            return {'status': 'error', 'message': str(e)}
            
    async def handle_template_deletion(self, data):
        """处理证书模板删除"""
        try:
            template_id = data.get('template_id')
            if not template_id:
                return {'status': 'error', 'message': '缺少模板ID'}
                
            # 删除证书模板
            success = self.db.delete_certificate_template(template_id)
            
            if success:
                return {'status': 'success', 'message': '证书模板删除成功'}
            else:
                return {'status': 'error', 'message': '证书模板删除失败'}
                
        except Exception as e:
            logging.error(f'处理证书模板删除错误: {e}')
            return {'status': 'error', 'message': str(e)}

    async def handle_certificate_application(self, data, client_addr=None):
        """处理证书申请"""
        try:
            # 参数验证
            if not data or not isinstance(data, dict):
                return {'status': 'error', 'message': '无效的6请求数据'}
                
            template_id = data.get('template_id')
            subject_name = data.get('subject_name')
            public_key = data.get('public_key')
            user_id = data.get('user_id')  # 可选参数，用于权限检查
            
            # 获取客户端地址
            writer = data.get('_writer')
            if writer:
                addr = writer.get_extra_info('peername')
                addr_str = 'Unknown' if addr is None else f'{addr[0]}:{addr[1]}'
                
                # 生成证书序列号并保存映射关系
                serial_number = self.crypto.generate_serial_number()
                self.cert_client_map[serial_number] = addr_str
            
            # 获取申请者详细信息
            organization = data.get('organization', '')
            department = data.get('department', '')
            email = data.get('email', '')
            usage = data.get('usage', '')
            remarks = data.get('remarks', '')

            # 验证必要参数
            if not all([template_id, subject_name, public_key]):
                return {'status': 'error', 'message': '缺少必要参数'}
                
            # 验证参数格式
            if not isinstance(subject_name, str) or len(subject_name) > 255:
                return {'status': 'error', 'message': '主题名称格式无效或超出长度限制'}
                
            if not isinstance(public_key, str):
                return {'status': 'error', 'message': '公钥格式无效'}

            # 获取证书模板信息
            template = self.db.get_certificate_template(template_id)
            if not template:
                return {'status': 'error', 'message': '证书模板不存在'}
                
            # 如果提供了用户ID，检查用户是否有权限使用该模板
            if user_id and not self.db.check_template_permission(template_id, user_id):
                return {'status': 'error', 'message': '用户无权使用此证书模板'}

            # 计算公钥指纹
            public_key_fingerprint = self.crypto.calculate_public_key_fingerprint(public_key)
            if not public_key_fingerprint:
                return {'status': 'error', 'message': '计算公钥指纹失败'}
            
            # 保存或获取密钥对记录
            if user_id:
                # 检查是否已存在该公钥的记录
                existing_key_pair = self.db.get_key_pair_by_fingerprint(public_key_fingerprint)
                if not existing_key_pair:
                    # 使用SM4加密公钥后存储
                    public_key_encrypted = self.crypto.sm4_encrypt(public_key)
                    if not public_key_encrypted:
                        return {'status': 'error', 'message': '加密公钥失败'}
                    
                    # 添加密钥对记录
                    if not self.db.add_key_pair(user_id, public_key_encrypted, public_key_fingerprint):
                        return {'status': 'error', 'message': '保存密钥对失败'}
                else:
                    # 检查是否属于当前用户
                    if existing_key_pair['user_id'] != user_id:
                        return {'status': 'error', 'message': '该公钥已由其他用户注册'}

            # 生成证书序列号 - 使用SM3哈希确保唯一性
            timestamp = datetime.now().timestamp()
            serial_number = self.crypto.sm3_hash(f"{subject_name}{timestamp}{public_key}")

            # 根据模板设置证书有效期
            issue_date = datetime.now()
            validity_period = int(template.get('validity_period', 365))  # 确保是整数，默认1年
            expiry_date = issue_date + timedelta(days=validity_period)

            # 生成证书签名 - 使用标准化的格式
            cert_data = json.dumps({
                "serial_number": serial_number,
                "subject_name": subject_name,
                "public_key": public_key,
                "issue_date": issue_date.isoformat(),
                "expiry_date": expiry_date.isoformat()
            })
            signature = self.crypto.sm2_sign(cert_data)

            # 保存证书，状态设为pending（待审核）
            conn = None
            cursor = None
            success = False
            try:
                conn = self.db.get_connection()
                if not conn:
                    self.log("无法获取数据库连接")
                    return {'status': 'error', 'message': '数据库连接失败'}
                    
                cursor = conn.cursor()
                
                # 记录SQL语句和参数，便于调试
                sql = """
                    INSERT INTO certificates 
                    (serial_number, subject_name, public_key_fingerprint, status, issue_date, expiry_date, 
                     signature, template_id, organization, department, email, usage_purpose, remarks)
                    VALUES (%s, %s, %s, 'pending', %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    serial_number, subject_name, public_key_fingerprint, issue_date, expiry_date,
                    signature, template_id, organization, department, email, usage, remarks
                )
                
                self.log(f"执行SQL: {sql}")
                self.log(f"参数: {params}")
                
                cursor.execute(sql, params)
                conn.commit()
                success = True
                self.log(f"证书申请数据已成功保存到数据库")
            except Exception as db_err:
                self.log(f"保存证书申请失败: {db_err}")
                if conn:
                    try:
                        conn.rollback()
                    except Exception as rollback_err:
                        self.log(f"回滚事务失败: {rollback_err}")
                success = False
            finally:
                if cursor:
                    try:
                        cursor.close()
                    except Exception as cursor_err:
                        self.log(f"关闭游标失败: {cursor_err}")
                if conn:
                    try:
                        conn.close()
                    except Exception as conn_err:
                        self.log(f"关闭数据库连接失败: {conn_err}")

            if success:
                self.log(f"证书申请已提交: {serial_number} - {subject_name}")
                print(f"已收到证书申请: {serial_number} - {subject_name}")
                
                # 记录证书申请事件
                request_data = {
                    'serial_number': serial_number,
                    'subject_name': subject_name,
                    'template_id': template_id,
                    'usage': usage
                }
                self.logger.log_certificate_event('申请', request_data)
                
                # 通知UI刷新证书列表
                if hasattr(self, 'ui') and self.ui:
                    self.ui.load_certificates()
                return {
                    'status': 'success',
                    'data': {
                        'serial_number': serial_number,
                        'subject_name': subject_name,
                        'issue_date': issue_date.isoformat(),
                        'expiry_date': expiry_date.isoformat(),
                        'status': 'pending',
                        'template_name': template.get('name')
                    }
                }
            else:
                return {'status': 'error', 'message': '证书申请保存失败'}

        except ValueError as e:
            self.log(f'处理证书申请参数错误: {e}')
            return {'status': 'error', 'message': f'参数错误: {str(e)}'}
        except Exception as e:
            self.log(f'处理证书申请错误: {e}')
            return {'status': 'error', 'message': str(e)}

    async def handle_certificate_verification(self, data):
        """处理证书验证"""
        try:
            # 验证输入参数
            if not data or not isinstance(data, dict):
                return {'status': 'error', 'message': '无效的1请求数据'}

            serial_number = data.get('serial_number')
            if not serial_number or not isinstance(serial_number, str):
                return {'status': 'error', 'message': '无效的证书序列号'}

            # 验证序列号长度
            if len(serial_number) > 64:
                return {'status': 'error', 'message': '证书序列号长度超出限制'}

            # 从数据库获取证书信息
            cert = self.db.verify_certificate(serial_number)
            if not cert:
                return {'status': 'error', 'message': '证书不存在'}
                
            # 获取完整证书信息，包括签名和公钥指纹
            conn = self.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute("""
                    SELECT serial_number, subject_name, public_key_fingerprint, status, 
                           issue_date, expiry_date, signature
                    FROM certificates
                    WHERE serial_number = %s
                """, (serial_number,))
                full_cert = cursor.fetchone()
            finally:
                cursor.close()
                conn.close()
                
            if not full_cert:
                return {'status': 'error', 'message': '无法获取完整证书信息'}
                
            # 确定证书状态
            cert_status = full_cert['status']
            status_message = '有效'
            is_valid = True
            
            # 检查是否已撤销
            if cert_status == 'revoked':
                status_message = '已撤销'
                is_valid = False
            
            # 检查是否过期
            from pytz import utc
            now_utc = datetime.now(utc)
            expiry_utc = full_cert['expiry_date'].astimezone(utc)
            
            if expiry_utc < now_utc:
                status_message = '已过期'
                is_valid = False
                
            
            # 重建签名时使用的数据
            cert_data = json.dumps({
                "serial_number": full_cert['serial_number'],
                "subject_name": full_cert['subject_name'],
                "public_key_fingerprint": full_cert['public_key_fingerprint'],
                "issue_date": full_cert['issue_date'].isoformat(),
                "expiry_date": full_cert['expiry_date'].isoformat()
            })
            
                
            # 返回验证结果
            return {
                'status': 'success',
                'data': {
                    'valid': is_valid,
                    'status_message': status_message,
                    'subject_name': full_cert['subject_name'],
                    'issue_date': full_cert['issue_date'].isoformat(),
                    'expiry_date': full_cert['expiry_date'].isoformat(),
                    'serial_number': full_cert['serial_number']
                }
            }

        except Exception as e:
            self.log(f'处理证书验证错误: {e}')
            return {'status': 'error', 'message': f'证书验证失败: {str(e)}'}

    async def handle_certificate_revocation(self, data, client_addr=None):
        """处理证书撤销，增加安全日志记录"""
        try:
            # 验证输入参数
            if not data or not isinstance(data, dict):
                return {'status': 'error', 'message': '无效的2请求数据'}

            serial_number = data.get('serial_number')
            revocation_reason = data.get('reason', '用户请求撤销')
            user_id = data.get('user_id')  # 可选参数，用于权限检查
            
            # 验证序列号
            if not serial_number or not isinstance(serial_number, str):
                return {'status': 'error', 'message': '无效的证书序列号'}
                
            # 验证序列号长度
            if len(serial_number) > 64:
                return {'status': 'error', 'message': '证书序列号长度超出限制'}
                
            # 检查证书是否存在
            cert = self.db.verify_certificate(serial_number)
            if not cert:
                return {'status': 'error', 'message': '证书不存在'}
                
            # 检查证书是否已经被撤销
            if cert.get('status') == 'revoked':
                return {'status': 'error', 'message': '证书已被撤销'}
                
            # 如果提供了用户ID，可以在这里进行权限检查
            # 例如，只有管理员或证书所有者才能撤销证书
            
            # 执行撤销操作
            self.log(f"尝试撤销证书: {serial_number}, 原因: {revocation_reason}")
            success = self.db.revoke_certificate(serial_number)

            if success:
                self.log(f"证书撤销成功: {serial_number}")
                # 可以在这里添加撤销记录到CRL（证书撤销列表）
                
                # 记录证书撤销事件
                revocation_data = {
                    'serial_number': serial_number,
                    'subject_name': cert.get('subject_name', '未知'),
                    'reason': revocation_reason,
                    'revocation_date': datetime.now().isoformat()
                }
                self.logger.log_certificate_event('撤销', revocation_data)
                
                return {
                    'status': 'success', 
                    'message': '证书已撤销',
                    'data': {
                        'serial_number': serial_number,
                        'revocation_date': datetime.now().isoformat(),
                        'reason': revocation_reason
                    }
                }
            else:
                self.log(f"证书撤销失败: {serial_number}")
                return {'status': 'error', 'message': '证书撤销失败'}

        except ValueError as e:
            self.log(f'处理证书撤销参数错误: {e}')
            return {'status': 'error', 'message': f'参数错误: {str(e)}'}
        except Exception as e:
            self.log(f'处理证书撤销错误: {e}')
            return {'status': 'error', 'message': f'证书撤销失败: {str(e)}'}
            
    async def handle_certificate_download(self, data):
        """处理证书下载"""
        try:
            # 验证输入参数
            if not data or not isinstance(data, dict):
                return {'status': 'error', 'message': '无效的3请求数据'}
                
            serial_number = data.get('serial_number')
            if not serial_number or not isinstance(serial_number, str):
                return {'status': 'error', 'message': '无效的证书序列号'}
                
            # 验证序列号长度
            if len(serial_number) > 64:
                return {'status': 'error', 'message': '证书序列号长度超出限制'}
                
            # 获取完整证书信息
            conn = self.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute("""
                    SELECT c.serial_number, c.subject_name, c.public_key_fingerprint, c.status, 
                           c.issue_date, c.expiry_date, c.signature, c.template_id,
                           t.name as template_name, t.key_usage
                    FROM certificates c
                    LEFT JOIN certificate_templates t ON c.template_id = t.id
                    WHERE c.serial_number = %s
                """, (serial_number,))
                cert = cursor.fetchone()
            finally:
                cursor.close()
                conn.close()
            
            if not cert:
                return {'status': 'error', 'message': '证书不存在'}
                
            # 确定证书状态
            status_message = '有效'
            if cert['status'] == 'revoked':
                status_message = '已撤销'
            
            # 检查是否过期
            from pytz import utc
            now_utc = datetime.now(utc)
            expiry_utc = cert['expiry_date'].astimezone(utc)
            
            if expiry_utc < now_utc:
                status_message = '已过期'
                
            # 构建证书内容 - 更详细的格式
            cert_content = """证书信息
                ==================
                """
            cert_content += f"序列号: {cert['serial_number']}\n"
            cert_content += f"主题名称: {cert['subject_name']}\n"
            cert_content += f"状态: {status_message}\n"
            cert_content += f"签发日期: {cert['issue_date'].strftime('%Y-%m-%d %H:%M:%S')}\n"
            cert_content += f"过期日期: {cert['expiry_date'].strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            # 添加模板信息（如果有）
            if cert.get('template_name'):
                cert_content += f"\n证书模板信息\n------------------\n"
                cert_content += f"模板名称: {cert['template_name']}\n"
                if cert.get('key_usage'):
                    cert_content += f"密钥用途: {cert['key_usage']}\n"
            
            # 添加公钥信息
            cert_content += f"\n公钥信息\n------------------\n"
            # 格式化显示公钥指纹（只显示部分）
            public_key_fingerprint = cert['public_key_fingerprint']
            if len(public_key_fingerprint) > 64:
                formatted_key = public_key_fingerprint[:32] + "..." + public_key_fingerprint[-32:]
            else:
                formatted_key = public_key_fingerprint
            cert_content += f"公钥指纹: {formatted_key}\n"
            
            # 添加签名信息
            cert_content += f"\n签名信息\n------------------\n"
            signature = cert['signature']
            if len(signature) > 64:
                formatted_sig = signature[:32] + "..." + signature[-32:]
            else:
                formatted_sig = signature
            cert_content += f"签名: {formatted_sig}\n"
            
            self.log(f"证书下载成功: {serial_number}")
            return {
                'status': 'success',
                'data': {
                    'content': cert_content,
                    'serial_number': cert['serial_number'],
                    'subject_name': cert['subject_name'],
                    'status': status_message,
                    'issue_date': cert['issue_date'].isoformat(),
                    'expiry_date': cert['expiry_date'].isoformat(),
                    'public_key_fingerprint': cert['public_key_fingerprint'],
                    'signature': cert['signature']
                }
            }
            
        except ValueError as e:
            self.log(f'处理证书下载参数错误: {e}')
            return {'status': 'error', 'message': f'参数错误: {str(e)}'}
        except Exception as e:
            self.log(f'处理证书下载错误: {e}')
            return {'status': 'error', 'message': f'证书下载失败: {str(e)}'}
            
            
    async def handle_certificate_approval(self, data):
        """处理证书审核通过"""
        try:
            # 参数验证
            if not data or not isinstance(data, dict):
                return {'status': 'error', 'message': '无效的4请求数据'}
                
            serial_number = data.get('serial_number')
            if not serial_number or not isinstance(serial_number, str):
                return {'status': 'error', 'message': '无效的证书序列号'}
            
            # 验证序列号长度
            if len(serial_number) > 64:
                return {'status': 'error', 'message': '证书序列号长度超出限制'}
            
            ## 检查客户端是否在线
            #client_alive = await self.check_client_alive(serial_number)
            #if not client_alive:
            #    return {'status': 'error', 'message': '客户端不在线，请等待客户端上线后再尝试审核'}
            
            # 检查证书是否存在且状态为pending
            conn = self.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            try:
                # 从certificates表中查找待审核的证书申请（pending状态）
                cursor.execute("""
                    SELECT serial_number, subject_name, public_key_fingerprint, status, issue_date, expiry_date, usage_purpose, template_id, organization, department, email
                    FROM certificates 
                    WHERE serial_number = %s AND status = 'pending'
                """, (serial_number,))
                certificate = cursor.fetchone()
                
                if not certificate:
                    return {'status': 'error', 'message': '证书不存在或状态不是待审核'}
                
                # 设置证书有效期
                issue_date = datetime.now()
                # 获取证书模板以确定有效期
                template_id = certificate.get('template_id')
                template = self.db.get_certificate_template(template_id)
                validity_period = template.get('validity_period', 365) if template else 365  # 默认1年
                expiry_date = issue_date + timedelta(days=validity_period)
                
                # 1. 生成证书内容
                cert_data = json.dumps({
                    "serial_number": certificate['serial_number'],
                    "subject_name": certificate['subject_name'],
                    "public_key_fingerprint": certificate['public_key_fingerprint'],
                    "issue_date": issue_date.isoformat(),
                    "expiry_date": expiry_date.isoformat(),
                    "organization": certificate.get('organization', ''),
                    "department": certificate.get('department', ''),
                    "email": certificate.get('email', ''),
                    "usage": certificate.get('usage_purpose', '')
                }, sort_keys=True)
                
                # 构建用户信息字段
                user_info = {
                    "name": certificate['subject_name'].split('CN=')[1].split(',')[0] if 'CN=' in certificate['subject_name'] else '',
                    "organization": certificate.get('organization', ''),
                    "department": certificate.get('department', ''),
                    "email": certificate.get('email', '')
                }
                user_info_json = json.dumps(user_info)
                
                # 2. 计算证书内容的SM3哈希值
                cert_hash = self.crypto.sm3_hash(cert_data)
                if not cert_hash:
                    return {'status': 'error', 'message': '计算证书哈希值失败'}
                
                # 3. 使用CA私钥对哈希值进行签名
                signature = self.crypto.sm2_sign(cert_hash)
                if not signature:
                    self.log(f"证书签名失败，哈希值: {cert_hash}")
                    return {'status': 'error', 'message': '证书签名失败'}
                
                # 4. 将证书保存到文件系统
                cert_dir = Path(__file__).parent / "certificates"
                cert_dir.mkdir(exist_ok=True)
                cert_file_path = cert_dir / f"{serial_number}.cer"
                
                # 格式化证书文件内容
                cert_file_content = f"""
                -----BEGIN CERTIFICATE-----
                    序列号: {serial_number}
                    主题: {certificate['subject_name']}
                    颁发者: CA Authority
                    有效期: {issue_date.strftime('%Y-%m-%d %H:%M:%S')} 至 {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}
                    用途: {certificate.get('usage_purpose', '')}
                    哈希值: {cert_hash}
                -----END CERTIFICATE-----"""
                
                # 保存证书文件
                try:
                    with open(cert_file_path, 'w', encoding='utf-8') as f:
                        f.write(cert_file_content)
                    self.log(f"证书文件已保存: {cert_file_path}")
                except Exception as file_err:
                    self.log(f"证书文件保存失败: {file_err}")
                    return {'status': 'error', 'message': f'保存证书文件失败: {str(file_err)}'}
                
                # 5. 更新certificates表中的证书状态为valid
                cursor.execute("""
                    UPDATE certificates 
                    SET status = 'valid',
                        issue_date = %s,
                        expiry_date = %s,
                        signature = %s
                    WHERE serial_number = %s
                """, (
                    issue_date,
                    expiry_date,
                    signature,
                    serial_number
                ))
                
                conn.commit()
                
                # 记录证书签发事件
                certificate_data = {
                    'serial_number': serial_number,
                    'subject_name': certificate['subject_name'],
                    'issuer_name': 'CN=CA Root,O=CA机构,C=CN',
                    'valid_from': issue_date.isoformat(),
                    'valid_to': expiry_date.isoformat(),
                    'content': cert_file_content
                }
                self.logger.log_certificate_event('签发', certificate_data)
                
                self.log(f"证书已审核通过: {serial_number}")
                return {
                    'status': 'success',
                    'message': '证书审核已通过',
                    'data': {
                        'serial_number': serial_number,
                        'status': 'valid',
                        'issue_date': issue_date.isoformat(),
                        'expiry_date': expiry_date.isoformat(),
                        'cert_file': str(cert_file_path)
                    }
                }
            except Exception as db_err:
                self.log(f"审核证书失败: {db_err}")
                conn.rollback()
                return {'status': 'error', 'message': f'审核证书失败: {str(db_err)}'}
            finally:
                cursor.close()
                conn.close()
                
        except Exception as e:
            self.log(f'处理证书审核错误: {e}')
            return {'status': 'error', 'message': str(e)}
    
    async def handle_change_password(self, data, client_addr=None):
        """处理修改密码请求"""
        try:
            # 参数验证
            if not data or not isinstance(data, dict):
                return {'status': 'error', 'message': '无效的请求数据'}
                
            current_password = data.get('current_password')
            new_password = data.get('new_password')
            user_id = data.get('user_id')
            
            if not current_password or not new_password:
                return {'status': 'error', 'message': '当前密码和新密码不能为空'}
            
            # 使用SM3进行密码哈希
            current_password_hash = self.crypto.sm3_hash(current_password)
            new_password_hash = self.crypto.sm3_hash(new_password)
            
            # 验证当前密码是否正确
            conn = self.db.get_connection()
            cursor = conn.cursor(dictionary=True, buffered=True)
            try:
                # 如果提供了用户ID，则同时检查用户ID和密码哈希
                if user_id:
                    cursor.execute("""
                        SELECT * FROM users 
                        WHERE id = %s AND password_hash = %s
                    """, (user_id, current_password_hash))
                else:
                    # 兼容旧版本，仅通过密码哈希查找用户
                    cursor.execute("""
                        SELECT * FROM users 
                        WHERE password_hash = %s
                    """, (current_password_hash,))
                user = cursor.fetchone()
                
                if not user:
                    cursor.close()
                    self.db.close_connection(conn)
                    return {'status': 'error', 'message': '当前密码不正确'}
                
                # 关闭当前游标，为更新操作创建新游标
                cursor.close()
                
                # 创建新游标执行更新操作
                update_cursor = conn.cursor(buffered=True)
                update_cursor.execute("""
                    UPDATE users 
                    SET password_hash = %s 
                    WHERE id = %s
                """, (new_password_hash, user['id']))
                
                conn.commit()
                update_cursor.close()
                self.db.close_connection(conn)
                self.log(f"用户 {user['username']} 修改了密码")
                return {'status': 'success', 'message': '密码修改成功'}
            except Exception as db_err:
                if conn:
                    conn.rollback()
                    self.db.close_connection(conn)
                raise db_err
            finally:
                if cursor:
                    try:
                        cursor.close()
                    except:
                        pass
        except Exception as e:
            self.log(f'处理修改密码请求失败: {e}')
            return {'status': 'error', 'message': f'修改密码失败: {str(e)}'}
    
    async def check_client_alive(self, serial_number):
        """检查指定证书申请的客户端是否在线"""
        try:
            # 获取证书对应的客户端地址
            client_addr = self.cert_client_map.get(serial_number)
            if not client_addr:
                self.log(f'未找到证书 {serial_number} 对应的客户端连接')
                return False

            # 获取客户端连接
            client_conn = self.client_connections.get(client_addr)
            if not client_conn:
                self.log(f'客户端 {client_addr} 的连接已断开')
                return False

            # 不发送心跳请求，直接返回客户端在线状态
            # 因为客户端已经连接到服务器，且连接仍然有效，所以可以认为客户端在线
            self.log(f'客户端 {client_addr} 在线，可以处理证书 {serial_number} 的审核')
            return True

        except Exception as e:
            self.log(f'检查客户端在线状态失败: {e}')
            return False

    async def handle_certificate_rejection(self, data, client_addr=None):
        """处理证书申请拒绝，增加安全日志记录"""
        try:
            # 参数验证
            if not data or not isinstance(data, dict):
                return {'status': 'error', 'message': '无效的5请求数据'}
                
            serial_number = data.get('serial_number')
            rejection_reason = data.get('reason', '申请不符合要求')
            user_id = data.get('user_id')  # 可选参数，用于安全日志
            
            if not serial_number or not isinstance(serial_number, str):
                return {'status': 'error', 'message': '无效的证书序列号'}
            
            # 验证序列号长度
            if len(serial_number) > 64:
                return {'status': 'error', 'message': '证书序列号长度超出限制'}
            
            # 检查证书是否存在且状态为pending
            conn = self.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute("""
                    SELECT serial_number, subject_name, status
                    FROM certificates 
                    WHERE serial_number = %s AND status = 'pending'
                """, (serial_number,))
                cert = cursor.fetchone()
                
                if not cert:
                    return {'status': 'error', 'message': '证书不存在或状态不是待审核'}
                
                # 更新证书状态为rejected
                cursor.execute("""
                    UPDATE certificates
                    SET status = 'rejected'
                    WHERE serial_number = %s
                """, (serial_number,))
                conn.commit()
                
                # 记录证书拒绝事件到安全日志
                rejection_data = {
                    'serial_number': serial_number,
                    'subject_name': cert.get('subject_name', '未知'),
                    'reason': rejection_reason
                }
                self.logger.log_certificate_event('拒绝', rejection_data)
                
                self.log(f"证书申请已拒绝: {serial_number}, 原因: {rejection_reason}")
                return {
                    'status': 'success',
                    'message': '证书申请已拒绝',
                    'data': {
                        'serial_number': serial_number,
                        'reason': rejection_reason
                    }
                }
            except Exception as db_err:
                self.log(f"拒绝证书申请失败: {db_err}")
                conn.rollback()
                return {'status': 'error', 'message': f'拒绝证书申请失败: {str(db_err)}'}
            finally:
                cursor.close()
                conn.close()
                
        except Exception as e:
            self.log(f'处理证书拒绝错误: {e}')
            return {'status': 'error', 'message': str(e)}

class SessionManager:
    """
    会话管理器，负责管理客户端与服务器之间的会话密钥
    """
    def __init__(self, db, crypto):
        self.db = db
        self.crypto = crypto
        # 初始化时确保会话表存在
        self._ensure_session_table()
        
        
    def _ensure_session_table(self):
        """确保会话表存在"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # 创建会话表 - 使用MySQL兼容的语法
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                session_key TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """)
            conn.commit()
            print("会话表创建或已存在")
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"创建会话表失败: {str(e)}")
            import traceback
            import logging
            traceback.print_exc()
        
    def create_session(self, user_id: int, encrypted_session_key: str) -> bool:
        """
        创建或更新用户会话
    
        Args:
            user_id: 用户ID
            encrypted_session_key: 使用服务器SM2公钥加密的SM4会话密钥（Base64编码）
        
        Returns:
            成功返回True，失败返回False
        """
        try:
            print(f"尝试为用户ID {user_id} 创建会话，加密会话密钥长度: {len(encrypted_session_key)}")
            
            # 确保会话密钥是Base64编码的，并进行解码
            try:
                # 解密会话密钥
                session_key = self.crypto.sm2_decrypt(encrypted_session_key)
                if not session_key:
                    print(f"会话密钥解密失败，用户ID: {user_id}")
                    # 删除可能存在的旧会话
                    self.delete_session(user_id)
                    return False
                
                # 验证解密后的会话密钥长度
                if len(session_key) == 0:
                    print(f"会话密钥解密结果为空，用户ID: {user_id}")
                    # 删除可能存在的旧会话
                    self.delete_session(user_id)
                    return False
                
                # 解密后的结果是十六进制字符串，需要转换回二进制数据
                try:
                    # 将十六进制字符串转换为二进制数据
                    session_key_bytes = bytes.fromhex(session_key)
                    session_key = session_key_bytes
                    print(f"会话密钥十六进制转换成功，长度: {len(session_key)}字节")
                except Exception as hex_err:
                    print(f"会话密钥十六进制转换失败: {str(hex_err)}")
                    # 如果转换失败，保持原样
                    pass
                
                print(f"会话密钥解密成功，长度: {len(session_key)}，内容: {session_key[:5]}...")
            except Exception as e:
                print(f"会话密钥解密过程发生错误: {str(e)}")
                return False
        
            # 获取数据库连接
            conn = self.db.get_connection()
            cursor = conn.cursor()
        
            try:
               # 检查是否已存在会话
                cursor.execute(
                    "SELECT id FROM sessions WHERE user_id = %s",
                    (user_id,)
                )
                existing_session = cursor.fetchone()
            
                # 设置会话过期时间（7天后）
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                expiry_time = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            
                print(f"当前时间: {current_time}, 过期时间: {expiry_time}")
            
                if existing_session:
                    # 更新现有会话
                    print(f"更新用户ID {user_id} 的现有会话")
                    cursor.execute(
                        "UPDATE sessions SET session_key = %s, expires_at = %s WHERE user_id = %s",
                        (session_key, expiry_time, user_id)
                    )
                else:
                    # 创建新会话
                    print(f"为用户ID {user_id} 创建新会话")
                    cursor.execute(
                        """INSERT INTO sessions 
                           (user_id, session_key, created_at, expires_at) 
                           VALUES (%s, %s, %s, %s)""",
                        (user_id, session_key, current_time, expiry_time)
                    )
            
                # 提交事务
                conn.commit()
                print(f"用户ID {user_id} 的会话已成功保存到数据库")
            
                # 验证会话是否真的保存了
                cursor.execute("SELECT COUNT(*) FROM sessions WHERE user_id = %s", (user_id,))
                count = cursor.fetchone()[0]
                print(f"数据库中用户ID {user_id} 的会话数量: {count}")
            
                # 如果验证失败，尝试查看具体错误
                if count == 0:
                    print("警告: 会话似乎没有保存到数据库")
                    # 检查表结构
                    try:
                        cursor.execute("DESCRIBE sessions")
                        columns = cursor.fetchall()
                        print(f"会话表结构: {columns}")
                    except Exception as struct_err:
                        print(f"无法获取表结构: {str(struct_err)}")
            
                return True
            except Exception as e:
                conn.rollback()
                print(f"创建会话失败: {str(e)}")
                import traceback
                import logging
                traceback.print_exc()
            
                # 尝试检查数据库连接状态
                try:
                    cursor.execute("SELECT 1")
                    print("数据库连接正常")
                except Exception as conn_err:
                    print(f"数据库连接异常: {str(conn_err)}")
            
                return False
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            print(f"会话创建过程发生错误: {str(e)}")
            import traceback
            import logging
            traceback.print_exc()
            return False
    
    def get_session(self, user_id):
        """获取用户的会话
        
        Args:
            user_id: 用户ID
            
        Returns:
            成功返回会话信息，失败或不存在返回None
        """
        try:
            # 查询会话
            result = self.db.query_one(
                """
                SELECT id, user_id, session_key, created_at, expires_at
                FROM sessions
                WHERE user_id = ? AND expires_at > ?
                """,
                (user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            
            if not result:
                return None
                
            return {
                "id": result[0],
                "user_id": result[1],
                "session_key": result[2],
                "created_at": result[3],
                "expires_at": result[4]
            }
            
        except Exception as e:
            print(f"获取会话失败: {str(e)}")
            return None


    def get_session_key(self, user_id: int) -> Optional[str]:
        """
        获取用户的会话密钥
        
        Args:
            user_id: 用户ID
            
        Returns:
            成功返回会话密钥，失败返回None
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            try:
                # 获取会话密钥并检查是否过期
                cursor.execute(
                    "SELECT session_key, expires_at FROM sessions WHERE user_id = %s",
                    (user_id,)
                )
                result = cursor.fetchone()
                
                if not result:
                    return None
                    
                session_key, expires_at = result
                
                # 检查会话是否过期
                if expires_at < datetime.now():
                    # 会话已过期，删除
                    cursor.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))
                    conn.commit()
                    return None
                    
                return session_key
            except Exception as e:
                print(f"获取会话密钥失败: {str(e)}")
                return None
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            print(f"获取会话密钥过程发生错误: {str(e)}")
            return None
    
    def delete_session(self, user_id: int) -> bool:
        """
        删除用户会话
        
        Args:
            user_id: 用户ID
            
        Returns:
            成功返回True，失败返回False
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                print(f"删除会话失败: {str(e)}")
                return False
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            print(f"删除会话过程发生错误: {str(e)}")
            return False
    
    def encrypt_with_session_key(self, user_id: int, data: Dict) -> Optional[str]:
        """
        使用会话密钥加密数据
        
        Args:
            user_id: 用户ID
            data: 要加密的数据
            
        Returns:
            成功返回加密后的数据，失败返回None
        """
        try:
            # 获取会话密钥
            session_key = self.get_session_key(user_id)
            if not session_key:
                return None
                
            # 序列化数据
            json_data = json.dumps(data).encode()
            
            # 使用会话密钥加密数据
            encrypted_data = self.crypto.sm4_encrypt_with_key(json_data, session_key)
            if not encrypted_data:
                return None
                
            return base64.b64encode(encrypted_data).decode()
        except Exception as e:
            print(f"使用会话密钥加密数据失败: {str(e)}")
            return None
    
    def decrypt_with_session_key(self, user_id: int, encrypted_data: str) -> Optional[Dict]:
        """
        使用会话密钥解密数据
        
        Args:
            user_id: 用户ID
            encrypted_data: 加密的数据
            
        Returns:
            成功返回解密后的数据，失败返回None
        """
        try:
            # 获取会话密钥
            session_key = self.get_session_key(user_id)
            if not session_key:
                return None
                
            # 解码Base64
            encrypted_bytes = base64.b64decode(encrypted_data)
            
            # 使用会话密钥解密数据
            decrypted_data = self.crypto.sm4_decrypt_with_key(encrypted_bytes, session_key)
            if not decrypted_data:
                return None
                
            # 解析JSON
            return json.loads(decrypted_data.decode())
        except Exception as e:
            print(f"使用会话密钥解密数据失败: {str(e)}")
            return None

if __name__ == '__main__':
    server = CAServer()
    asyncio.run(server.start())