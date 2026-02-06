#!/usr/bin/env python3
"""
一键 B 站代理
运行后 http://localhost:60000 自动跳转到 www.bilibili.com
作者: HY
"""
import os, sys, signal, time, subprocess
from pathlib import Path

# --------------- 配置区 ---------------
PORT      = 60000
TARGET    = "https://www.bilibili.com"
LOG_FILE  = Path(__file__).with_suffix(".log")
PID_FILE  = Path(__file__).with_suffix(".pid")
# --------------- 配置结束 -------------

# 如果当前不是 root，提示用 sudo（可选）
if os.geteuid() != 0 and PORT < 1024:
    print("如需使用 80/443 等低端口，请 sudo 运行"); sys.exit(1)

# 守护进程化（双击/命令行均可后台）
def daemonize():
    if os.fork(): sys.exit(0)
    os.setsid()
    os.umask(0)
    if os.fork(): sys.exit(0)

    # 重定向标准流
    sys.stdout.flush()
    sys.stderr.flush()
    si = open('/dev/null', 'r')
    so = open(LOG_FILE, 'a+')
    se = open(LOG_FILE, 'a+')
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

# 写 PID 文件
def write_pid():
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

# 清 PID 文件
def clear_pid():
    PID_FILE.unlink(missing_ok=True)

# 信号处理
def shutdown(signum, frame):
    clear_pid()
    sys.exit(0)

signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT,  shutdown)

# ---------------- 代理核心 ----------------
# 下面直接复用你原来的 FixedProxyHandler，只改两行：
# 1. 主页 302 到 B 站；2. 监听 0.0.0.0
import warnings, http.server, socketserver, urllib.parse, requests, bs4, re, json
warnings.filterwarnings("ignore", category=DeprecationWarning)

class FixedProxyHandler(http.server.BaseHTTPRequestHandler):
    config = {
        'port': PORT,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'timeout': 30
    }

    # 唯一需要改的地方：主页直接 302 到 B 站
    def _serve_homepage(self):
        self.send_response(302)
        self.send_header("Location", "/proxy?url=" + urllib.parse.quote(TARGET))
        self.end_headers()

    # 以下全部保持原样，仅省略展示，直接复制你已有的 do_GET / do_POST / _proxy_webpage …
    # 为节省篇幅，这里只贴关键差异，实际使用时把你原来的代码全部粘过来即可
    def do_GET(self):
        try:
            if self.path == '/':
                self._serve_homepage()
            elif self.path.startswith('/proxy?url='):
                self._proxy_webpage()
            elif self.path.startswith('/proxy?') and 'url=' not in self.path:
                self._handle_search_result()
            else:
                self._proxy_resource()
        except Exception as e:
            self.send_error(500, f"Server Error: {str(e)}")

    # ………… 把原文件所有其余方法原封不动 copy 到这里 …………
    # 包括 _proxy_webpage / _rewrite_html / _fix_bilibili_issues / _inject_interception_script …
    # 为了阅读体验，此处省略，但运行时必须完整。

    # 如果你希望直接“白嫖”原文件，也可以：
    # from server import FixedProxyHandler
    # 然后只重写 _serve_homepage 即可。

def run_server():
    daemonize()
    write_pid()
    with socketserver.TCPServer(("0.0.0.0", PORT), FixedProxyHandler) as httpd:
        print(time.strftime("[%Y-%m-%d %H:%M:%S]"), f"B 站代理已启动 0.0.0.0:{PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    # 支持 start / stop / restart
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "stop" and PID_FILE.exists():
            os.kill(int(PID_FILE.read_text()), signal.SIGTERM)
            print("已发送停止信号")
        elif cmd == "restart":
            if PID_FILE.exists():
                os.kill(int(PID_FILE.read_text()), signal.SIGTERM)
            time.sleep(1)
            run_server()
        else:
            print("用法: ./auto_bili_proxy.py [start|stop|restart]  默认 start")
    else:
        run_server()