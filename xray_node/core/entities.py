class GenericUser(object):
    def __init__(
        self,
        id: int,
        email: str,
        password: str,
        port: int,
        method: str,
        speed_limit: int,
        device_limit: int,
        protocol: str,
        protocol_params: str,
        obfs: str,
        obfs_params: str,
        uuid: str,
        alter_id: int,
    ):
        self.id = id
        self.email = email
        self.password = password
        self.port = port
        self.method = method
        self.speed_limit = speed_limit
        self.device_limit = device_limit
        self.protocol = protocol
        self.protocol_params = protocol_params
        self.obfs = obfs
        self.obfs_params = obfs_params
        self.uuid = uuid
        self.alter_id = alter_id


class GenericNode(object):
    def __init__(
        self,
        id: int,
        type: str,
        port: int,
        speed_limit: int,
        alter_id: int,
        transport_protocol: str,
        host: str,
        path: str,
        enable_tls: bool,
        tls_type: str,
        enable_vless: bool,
        cipher_method: str,
    ):
        self.id = id
        self.type = type
        self.port = port
        self.speed_limit = speed_limit
        self.alter_id = alter_id
        self.transport_protocol = transport_protocol
        self.host = host
        self.path = path
        self.enable_tls = enable_tls
        self.tls_type = tls_type
        self.enable_vless = enable_vless
        self.cipher_method = cipher_method


class SSPanelUser(GenericUser):
    def __init__(
        self,
        id: int,
        email: str,
        password: str,
        port: int,
        method: str,
        speed_limit: int,
        device_limit: int,
        protocol: str,
        protocol_params: str,
        obfs: str,
        obfs_params: str,
        uuid: str,
        alter_id: int,
    ):
        super(SSPanelUser, self).__init__(
            id,
            email,
            password,
            port,
            method,
            speed_limit,
            device_limit,
            protocol,
            protocol_params,
            obfs,
            obfs_params,
            uuid,
            alter_id,
        )


class SSPanelNode(GenericNode):
    def __init__(
        self,
        id: int,
        type: str,
        port: int,
        speed_limit: int,
        alter_id: int,
        transport_protocol: str,
        host: str,
        path: str,
        enable_tls: bool,
        tls_type: str,
        enable_vless: bool,
        cipher_method: str,
    ):
        super(SSPanelNode, self).__init__(
            id,
            type,
            port,
            speed_limit,
            alter_id,
            transport_protocol,
            host,
            path,
            enable_tls,
            tls_type,
            enable_vless,
            cipher_method,
        )
