from dataclasses import dataclass


@dataclass
class GenericUser(object):
    user_id: int
    panel_name: str
    node_id: int
    email: str
    speed_limit: int


@dataclass
class SSUser(GenericUser):
    password: str
    method: str
    is_multi_user: bool = False
    listen_port: int = 0


@dataclass
class VMessUser(GenericUser):
    uuid: str


@dataclass
class VLessUser(VMessUser):
    pass


@dataclass
class TrojanUser(VMessUser):
    pass


@dataclass
class GenericNode(object):
    node_id: int
    panel_name: str
    listen_port: int
    listen_host: str


@dataclass
class SSNode(GenericNode):
    pass


@dataclass
class VMessNode(GenericNode):
    alter_id: int
    transport: str
    enable_tls: bool
    tls_type: str
    path: str
    host: str


@dataclass
class VLessNode(VMessNode):
    pass


@dataclass
class TrojanNode(GenericNode):
    host: str
    enable_xtls: bool
    enable_vless: bool


@dataclass
class SSPanelOnlineIPData(object):
    user_id: int
    ip: str


@dataclass
class SSPanelTrafficData(object):
    user_id: int
    upload: int
    download: int
