#!/usr/bin/env python3
"""
标准启动脚本 - 用于本地开发环境
"""

import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from network import AsyncClient
from login_ui import LoginDialog as LoginUI
from main_ui import CAClient
import asyncio

def main():
    app = QApplication(sys.argv)

    # 创建事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # 创建网络客户端实例
        client = AsyncClient()
        client.start()

        # 显示登录对话框
        login_dialog = LoginUI(client)

        # 如果登录成功，显示主界面
        if login_dialog.exec_() == login_dialog.Accepted:
            try:
                main_window = CAClient(client)
                # 等待异步初始化完成
                loop.run_until_complete(main_window.async_init())
                main_window.show()
                app.exec_()
            except Exception as e:
                print(f"创建主界面时发生错误: {str(e)}")
                QMessageBox.critical(None, "错误", f"创建主界面失败: {str(e)}")
                sys.exit(1)
        else:
            sys.exit(0)
    except Exception as e:
        print(f"程序启动时发生错误: {str(e)}")
        QMessageBox.critical(None, "错误", f"程序启动失败: {str(e)}")
        sys.exit(1)
    finally:
        # 清理事件循环
        try:
            pending = asyncio.all_tasks(loop)
            loop.run_until_complete(asyncio.gather(*pending))
            loop.stop()
            loop.close()
        except Exception as e:
            print(f"清理事件循环时发生错误: {str(e)}")
            # 确保在发生错误时也能正确清理资源
            if loop and loop.is_running():
                loop.stop()
            if loop and not loop.is_closed():
                loop.close()

if __name__ == "__main__":
    main()