import threading
from pathlib import Path

import tomlkit


def init_config(target: Path):
    """
    初始化配置文件
    :param target:
    :return:
    """
    template = """# xray-node 配置文件

[log]
level = "info" # 日志等级，debug/info/warning/error

[user]
mode = "local" # 用户管理模式，local 通过本地文件管理，remote 通过面板管理

[[user.clients]]
type = "shadowsocks"
password = "aabbccdd"
cipher_type = "aes-256-gcm"

[[user.clients]]
type = "shadowsocks"
password = "aabbccdd"
cipher_type = "aes-256-gcm"

[[user.clients]]
type = "shadowsocks"
password = "aabbccdd"
cipher_type = "aes-256-gcm"

[xray.api]
host = "127.0.0.1"
port = 10085

[[xray.inbounds]]
listen = "0.0.0.0"
port = 1234
protocol = "shadowsocks"
"""

    with open(target, "w") as f:
        f.write(template)


class Config(object):
    _instance_lock = threading.Lock()

    def __init__(self, cfg: Path = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if cfg:
            fn = cfg
        else:
            fn = Path("./xnode.yaml")

        if not fn.exists():
            init_config(target=fn)

        with open(fn, "r") as f:
            self.content = tomlkit.parse(f.read())

        self.log_level = self.content["log"]["level"]

        self.user_mode = self.content["user"]["mode"]

        self.clients = self.content["user"]["clients"]
        self.inbounds = self.content["xray"]["inbounds"]

        self.local_api_host = self.content["xray"]["api"]["host"]
        self.local_api_port = self.content["xray"]["api"]["port"]

    def __new__(cls, cfg: Path = None, *args, **kwargs):
        if not hasattr(Config, "_instance"):
            with Config._instance_lock:
                if not hasattr(Config, "_instance"):
                    Config._instance = super(Config, cls).__new__(cls, *args, **kwargs)
        return Config._instance
