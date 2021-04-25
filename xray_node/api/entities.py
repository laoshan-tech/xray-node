class GenericUser(object):
    def __init__(self, user_id: int, speed_limit: int):
        self.user_id = user_id
        self.speed_limit = speed_limit


class SSUser(GenericUser):
    def __init__(self, user_id: int, speed_limit: int, password: str, method: str, is_multi_user: bool = False):
        super(SSUser, self).__init__(user_id=user_id, speed_limit=speed_limit)
        self.method = method
        self.password = password
        self.is_multi_user = is_multi_user


class VMessUser(GenericUser):
    def __init__(self, user_id: int, speed_limit: int, uuid: str):
        super(VMessUser, self).__init__(user_id=user_id, speed_limit=speed_limit)
        self.uuid = uuid


class VLessUser(VMessUser):
    def __init__(self, user_id: int, speed_limit: int, uuid: str):
        super(VLessUser, self).__init__(user_id=user_id, speed_limit=speed_limit, uuid=uuid)


class TrojanUser(VMessUser):
    def __init__(self, user_id: int, speed_limit: int, uuid: str):
        super(TrojanUser, self).__init__(user_id=user_id, speed_limit=speed_limit, uuid=uuid)


class GenericNode(object):
    def __init__(self, node_id: int, panel_name: str, listen_port: int, listen_host: str = "0.0.0.0"):
        self.node_id = node_id
        self.panel_name = panel_name
        self.listen_port = listen_port
        self.listen_host = listen_host


class SSNode(GenericNode):
    def __init__(self, node_id: int, panel_name: str, listen_port: int):
        super(SSNode, self).__init__(node_id=node_id, panel_name=panel_name, listen_port=listen_port)


class VMessNode(GenericNode):
    def __init__(
        self,
        node_id: int,
        panel_name: str,
        listen_port: int,
        alter_id: int,
        transport: str,
        enable_tls: bool,
        tls_type: str,
        path: str,
        host: str,
        listen_host: str = "0.0.0.0",
    ):
        super(VMessNode, self).__init__(
            node_id=node_id, panel_name=panel_name, listen_port=listen_port, listen_host=listen_host
        )
        self.alter_id = alter_id
        self.transport = transport
        self.enable_tls = enable_tls
        self.tls_type = tls_type
        self.path = path
        self.host = host


class VLessNode(VMessNode):
    def __init__(
        self,
        node_id: int,
        panel_name: str,
        listen_port: int,
        alter_id: int,
        transport: str,
        enable_tls: bool,
        tls_type: str,
        path: str,
        host: str,
        listen_host: str = "0.0.0.0",
    ):
        super(VLessNode, self).__init__(
            node_id=node_id,
            panel_name=panel_name,
            listen_port=listen_port,
            listen_host=listen_host,
            alter_id=alter_id,
            transport=transport,
            enable_tls=enable_tls,
            tls_type=tls_type,
            path=path,
            host=host,
        )


class TrojanNode(GenericNode):
    def __init__(
        self,
        node_id: int,
        panel_name: str,
        listen_port: int,
        host: str,
        enable_xtls: bool = False,
        enable_vless: bool = False,
        listen_host: str = "0.0.0.0",
    ):
        super(TrojanNode, self).__init__(
            node_id=node_id, panel_name=panel_name, listen_port=listen_port, listen_host=listen_host
        )
        self.host = host
        self.enable_xtls = enable_xtls
        self.enable_vless = enable_vless