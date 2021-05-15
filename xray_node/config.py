import logging
import threading
from pathlib import Path
from typing import List, Union

import tomlkit

from xray_node.api import entities
from xray_node.utils.consts import NodeTypeEnum

logger = logging.getLogger(__name__)


def init_config(target: Path):
    """
    初始化配置文件
    :param target:
    :return:
    """
    template = """# xray-node

[log]
level = "info" # debug/info/warning/error

[user]
mode = "local" # local/remote

[panel]
type = "sspanel" # sspanel/v2board/django-sspanel
endpoint = "http://xxx.xxxx.com/"
node_id = 1
api_key = "key"

[[user.clients]]
type = "shadowsocks"
password = "aabbccdd"
speed_limit = 0
cipher_type = "aes-256-gcm"

[[user.clients]]
type = "shadowsocks"
password = "aabbccdd"
speed_limit = 0
cipher_type = "aes-256-gcm"

[[user.clients]]
type = "shadowsocks"
password = "aabbccdd"
speed_limit = 0
cipher_type = "aes-256-gcm"

[[user.clients]]
type = "vmess"
uuid = "595abb61-be40-4cee-afb4-d889dcd510cb"
speed_limit = 0

[xray.api]
host = "127.0.0.1"
port = 10085

[[xray.inbounds]]
listen = "0.0.0.0"
port = 1234
protocol = "shadowsocks"
"""
    target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        f.write(template)


class Config(object):
    _instance_lock = threading.Lock()

    def __init__(self, cfg: Path = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if cfg:
            self.fn = cfg
        else:
            self.fn = Path.home() / "xnode.toml"

        if not self.fn.exists():
            init_config(target=self.fn)

        with open(self.fn, "r", encoding="utf-8") as f:
            self.content = tomlkit.parse(f.read())

        self.log_level = self.content["log"]["level"]

        self.user_mode = self.content["user"]["mode"]
        if self.user_mode == "remote":
            self.panel_type = self.content["panel"]["type"]
            self.endpoint = self.content["panel"]["endpoint"]
            self.api_key = self.content["panel"]["api_key"]
            self.node_id = self.content["panel"]["node_id"]

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

    def load_local_users(
        self,
    ) -> List[Union[entities.SSUser, entities.VMessUser, entities.VLessUser, entities.TrojanUser]]:
        """
        通过配置文件加载用户信息
        :return:
        """
        clients = self.content["user"]["clients"]

        users = []
        for idx, c in enumerate(clients):
            try:
                if c["type"] in (NodeTypeEnum.Shadowsocks.value, NodeTypeEnum.ShadowsocksR.value):
                    u = entities.SSUser(
                        user_id=idx,
                        panel_name="local",
                        email=f"{idx}@local",
                        speed_limit=c.get("speed_limit", 0),
                        password=c["password"],
                        method=c["cipher_type"],
                    )
                    users.append(u)
                elif c["type"] == NodeTypeEnum.VMess.value:
                    u = entities.VMessUser(
                        user_id=idx,
                        panel_name="local",
                        email=f"{idx}@local",
                        speed_limit=c.get("speed_limit", 0),
                        uuid=c["uuid"],
                    )
                    users.append(u)
                elif c["type"] == NodeTypeEnum.VLess.value:
                    u = entities.VLessUser(
                        user_id=idx,
                        panel_name="local",
                        email=f"{idx}@local",
                        speed_limit=c.get("speed_limit", 0),
                        uuid=c["uuid"],
                    )
                    users.append(u)
                elif c["type"] == NodeTypeEnum.Trojan.value:
                    u = entities.TrojanUser(
                        user_id=idx,
                        panel_name="local",
                        email=f"{idx}@local",
                        speed_limit=c.get("speed_limit", 0),
                        uuid=c["uuid"],
                    )
                    users.append(u)
                else:
                    logger.error(f"不支持的用户类型 {c}")
                    continue
            except KeyError as e:
                logger.error(f"从配置文件中加载用户时出错 {e}")
                continue

        return users
