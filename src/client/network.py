import socket
import json
import time
from PyQt5.QtCore import QThread, pyqtSignal

class AsyncClient(QThread):
    response_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, host='127.0.0.1', port=8888):
        super().__init__()
        self.host = host
        self.port = port
        self.sock = None
        self._connection_event = False

    def connect(self):
        retry_count = 0
        max_retries = 5
        base_delay = 1.0
        
        while retry_count < max_retries:
            try:
                # 关闭现有连接
                if self.sock:
                    try:
                        self.sock.close()
                    except:
                        pass
                    self.sock = None
                
                # 显示连接信息
                self.error_occurred.emit(f'正在连接到服务器 {self.host}:{self.port}... (尝试 {retry_count + 1}/{max_retries})')
                
                # 创建新的socket连接
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(30.0)  # 设置超时时间为30秒
                self.sock.connect((self.host, self.port))
                
                # 设置连接成功标志
                self._connection_event = True
                self.error_occurred.emit(f'成功连接到服务器 {self.host}:{self.port}')
                return True
                
            except socket.timeout:
                self.error_occurred.emit(f'连接超时 (尝试 {retry_count + 1}/{max_retries})')
                retry_count += 1
                time.sleep(base_delay * (2 ** retry_count))
            
            except Exception as e:
                self.error_occurred.emit(f'连接失败: {str(e)}（尝试 {retry_count + 1}/{max_retries}）')
                retry_count += 1
                time.sleep(base_delay * (2 ** retry_count))
        
        # 连接失败
        self._connection_event = False
        self.error_occurred.emit(f'无法连接到服务器 {self.host}:{self.port}，请检查服务器是否运行')
        return False

    def run(self):
        try:
            if self.connect():
                self.response_received.emit({'status': 'success', 'message': '连接服务器成功'})
        except Exception as e:
            self.error_occurred.emit(str(e))

    def handle_heartbeat(self, data):
        """处理心跳请求"""
        try:
            # 检查连接状态
            if not self.sock:
                return {'status': 'error', 'message': '客户端未连接'}
            
            # 获取证书序列号（如果有）
            serial_number = data.get('serial_number', '')
            
            # 构建心跳响应
            response = {
                'status': 'success', 
                'message': '客户端在线',
                'data': {'serial_number': serial_number}
            }
            
            # 发送心跳响应
            try:
                response_str = json.dumps(response)
                self.sock.sendall(response_str.encode('utf-8'))
                return response
            except socket.error as e:
                self.error_occurred.emit(f'发送心跳响应失败: {str(e)}')
                return {'status': 'error', 'message': '连接异常'}
        except Exception as e:
            self.error_occurred.emit(f'处理心跳请求失败: {str(e)}')
            return {'status': 'error', 'message': str(e)}

    def send_request(self, action, data):
        """发送请求"""
        # 如果是心跳请求，直接在本地处理
        if action == 'heartbeat':
            return self.handle_heartbeat(data)
            
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                if not self.sock:
                    # 尝试重新连接
                    self.error_occurred.emit(f'连接已断开，正在尝试重新连接...')
                    if not self.connect():
                        return {'status': 'error', 'message': f'无法连接到服务器 {self.host}:{self.port}，请检查服务器是否运行'}

                # 构建请求
                request = {
                    'action': action,
                    'data': data
                }
                request_str = json.dumps(request)
                
                
                # 发送请求
                self.sock.sendall(request_str.encode('utf-8'))
                
                # 接收响应
                response_data = b''
                self.sock.settimeout(10.0)  # 增加接收超时时间到30秒
                
                # 使用缓冲区接收数据
                buffer_size = 8192  # 增加缓冲区大小
                start_time = time.time()
                
                
                while True:
                    try:
                        chunk = self.sock.recv(buffer_size)
                        if not chunk:
                            break
                        response_data += chunk
                        if len(chunk) < buffer_size:
                            break
                            
                        # 检查是否超过总超时时间
                        if time.time() - start_time > 30:
                            raise socket.timeout()
                            
                    except socket.timeout:
                        if len(response_data) > 0:
                            # 如果已经接收到部分数据，尝试解析
                            self.error_occurred.emit(f'接收超时但已有部分数据，尝试解析...')
                            break
                        self.error_occurred.emit(f'接收完全超时，未收到任何数据')
                        raise  # 重新抛出异常
                
                # 解析响应
                response = json.loads(response_data.decode('utf-8'))
                
                # 如果是心跳请求，直接处理
                if response.get('action') == 'heartbeat':
                    return self.handle_heartbeat(response.get('data', {}))
                
                # 发送响应信号
                self.response_received.emit(response)
                return response
                
            except socket.timeout:
                self.error_occurred.emit(f'请求超时 (尝试 {attempt + 1}/{max_retries})')
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return {'status': 'error', 'message': '请求超时'}
                
            except json.JSONDecodeError as e:
                self.error_occurred.emit(f'解析响应失败: {str(e)}')
                return {'status': 'error', 'message': '无效的响应格式'}
                
            except Exception as e:
                self.error_occurred.emit(f'请求失败: {str(e)}')
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return {'status': 'error', 'message': str(e)}
                
        return {'status': 'error', 'message': '请求失败，已达到最大重试次数'}

    def is_connected(self):
        """检查连接状态"""
        if not self._connection_event or not self.sock:
            return False
            
        try:
            # 不发送心跳包，只检查socket状态
            return self._connection_event and self.sock is not None
        except Exception:
            # 任何异常都视为连接已断开
            self._connection_event = False
            return False

    def stop(self):
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None
        self._connection_event = False
        self.terminate()
        self.wait(2000)