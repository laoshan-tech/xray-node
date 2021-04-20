class XrayError(Exception):
    def __init__(self, detail):
        self.detail = detail


class APIError(Exception):
    def __init__(self, msg):
        self.msg = msg


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


class AddressAlreadyInUseError(XrayError):
    def __init__(self, detail, port):
        super(AddressAlreadyInUseError, self).__init__(detail)
        self.port = port


class FetchNodeInfoError(APIError):
    def __init__(self, msg):
        super(FetchNodeInfoError, self).__init__(msg=msg)
