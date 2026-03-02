#!/usr/bin/env python3
"""
CA 客户端主程序 - Docker 兼容版本
"""

import sys
import os

if __name__ == "__main__":
    # 检查是否在 Docker 环境中
    in_docker = os.environ.get('DOCKER_ENV') == 'true' or os.path.exists('/.dockerenv')
    
    if in_docker:
        print("Docker 环境检测到，使用 Docker 配置")
        # 在 Docker 环境中，导入并使用新的启动脚本
        try:
            from start_client import main as docker_main
            docker_main()
        except ImportError as e:
            print(f"导入 Docker 启动脚本失败: {e}")
            print("回退到标准启动方式")
            # 回退到标准启动
            from standard_start import main
            main()
    else:
        print("本地环境，使用标准配置")
        # 本地环境，使用标准启动
        from standard_start import main
        main()