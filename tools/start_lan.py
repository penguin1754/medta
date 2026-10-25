#!/usr/bin/env python3
"""局域网一键启动：让同一个 WiFi / 热点下的其他设备也能打开这个网页。

用法：
    python tools/start_lan.py            # 默认 8787 端口
    python tools/start_lan.py --port 9000

Windows 首次运行如果弹出防火墙提示，请勾选"专用网络"并允许访问，
否则同网段的手机/电脑连不上。
"""
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def lan_ips():
    """尽量列出本机各网卡的 IPv4（UDP connect 不会真的发包）。"""
    ips = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("223.5.5.5", 80))
            ips.append(s.getsockname()[0])
        finally:
            s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ips and not ip.startswith("127.") and not ip.startswith("169.254."):
                ips.append(ip)
    except OSError:
        pass
    return ips


def port_free(port):
    """判断端口是否真的能独占绑定（Windows 下用 SO_EXCLUSIVEADDRUSE 才准）。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        s.bind(("0.0.0.0", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def pick_port(start):
    if port_free(start):
        return start
    for cand in range(start + 1, start + 21):
        if port_free(cand):
            print("  端口 %d 已被占用（可能是上次没关的窗口），自动改用 %d。" % (start, cand))
            return cand
    print("  端口 %d 附近都被占用了，请手动指定 --port。" % start)
    sys.exit(1)


def main():
    port = "8787"
    if "--port" in sys.argv:
        port = sys.argv[sys.argv.index("--port") + 1]
    port = str(pick_port(int(port)))

    ips = lan_ips()
    print("=" * 58)
    print("局域网模式启动中……")
    if ips:
        for ip in ips:
            print("  同网段设备请打开：  http://%s:%s" % (ip, port))
    else:
        print("  没找到局域网 IP，请检查是否连着 WiFi。")
    print("  本机仍然可以打开：    http://127.0.0.1:%s" % port)
    print("  首次运行若弹防火墙提示，请允许访问专用网络。")
    print("=" * 58)

    cmd = [sys.executable, os.path.join("backend", "app.py"),
           "--host", "0.0.0.0", "--port", port]
    proc = subprocess.Popen(cmd, cwd=ROOT)

    def open_later():
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:%s" % port)

    threading.Thread(target=open_later, daemon=True).start()
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()


if __name__ == "__main__":
    main()
