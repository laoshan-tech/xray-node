import threading
from pathlib import Path

import tomlkit


async def init_config(target: Path):
    """
    初始化配置文件
    :param target:
    :return:
    """
    doc = tomlkit.document()
    doc.add(tomlkit.comment("xray-node 配置文件"))

    user = tomlkit.table()
    user.add("mode", "local")
    user["mode"].comment("用户管理模式，local 通过本地文件管理，remote 通过面板管理")
    doc.add("user", user)
    doc.add(tomlkit.nl())

    xray = tomlkit.table()
    xray._is_super_table = True
    api = tomlkit.table()
    api.add("host", "127.0.0.1")
    api.add("port", 10085)
    xray["api"] = api
    doc["xray"] = xray

    with open(target, "w") as f:
        f.write(tomlkit.dumps(doc))


class Config(object):
    _instance_lock = threading.Lock()

    def __init__(self, cfg: Path = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if cfg:
            fn = cfg
        else:
            fn = Path("./xnode.yaml")

        if fn.exists():
            with open(fn, "r") as f:
                self.content = tomlkit.parse(f.read())
        else:
            raise FileNotFoundError(f"{fn} does not exists")

        self.local_api_host = self.content["xray"]["api"]["host"]
        self.local_api_port = self.content["xray"]["api"]["port"]

    def __new__(cls, cfg, *args, **kwargs):
        if not hasattr(Config, "_instance"):
            with Config._instance_lock:
                if not hasattr(Config, "_instance"):
                    Config._instance = super(Config, cls).__new__(cls, *args, **kwargs)
        return Config._instance
