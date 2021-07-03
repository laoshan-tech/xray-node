class XrayError(Exception):
    def __init__(self, detail):
        self.detail = detail


class APIError(Exception):
    def __init__(self, msg):
        self.msg = msg


class DataError(Exception):
    def __init__(self, msg):
        self.msg = msg


class UnsupportedNode(DataError):
    def __init__(self, msg):
        super(UnsupportedNode, self).__init__(msg=msg)


class UnsupportedUser(DataError):
    def __init__(self, msg):
        super(UnsupportedUser, self).__init__(msg=msg)


class NodeDataNotFound(DataError):
    def __init__(self, msg):
        super(NodeDataNotFound, self).__init__(msg=msg)


class EmailExistsError(XrayError):
    def __init__(self, detail, email: str):
        super(EmailExistsError, self).__init__(detail)
        self.email = email


class EmailNotFoundError(XrayError):
    def __init__(self, detail, email: str):
        super(EmailNotFoundError, self).__init__(detail)
        self.email = email


class InboundTagNotFound(XrayError):
    def __init__(self, detail, inbound_tag: str):
        super(InboundTagNotFound, self).__init__(detail)
        self.inbound_tag = inbound_tag


class InboundTagAlreadyExists(XrayError):
    def __init__(self, detail, inbound_tag: str):
        super(InboundTagAlreadyExists, self).__init__(detail)
        self.inbound_tag = inbound_tag


class AddressAlreadyInUseError(XrayError):
    def __init__(self, detail, port):
        super(AddressAlreadyInUseError, self).__init__(detail)
        self.port = port


class APIStatusError(APIError):
    def __init__(self, msg):
        super(APIStatusError, self).__init__(msg=msg)


class APIContentError(APIError):
    def __init__(self, msg):
        super(APIContentError, self).__init__(msg=msg)


class UnsupportedAPI(APIError):
    def __init__(self, msg):
        super(UnsupportedAPI, self).__init__(msg=msg)


class FetchNodeInfoError(APIError):
    def __init__(self, msg):
        super(FetchNodeInfoError, self).__init__(msg=msg)


class ReportNodeStatsError(APIError):
    def __init__(self, msg):
        super(ReportNodeStatsError, self).__init__(msg=msg)


class ReportUserTrafficError(APIError):
    def __init__(self, msg):
        super(ReportUserTrafficError, self).__init__(msg=msg)
