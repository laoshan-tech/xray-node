from enum import Enum

from xray_rpc.common.net import network_pb2
from xray_rpc.proxy.shadowsocks.config_pb2 import (
    NONE,
    UNKNOWN,
    AES_128_CFB,
    AES_256_CFB,
    CHACHA20,
    CHACHA20_IETF,
    CHACHA20_POLY1305,
    AES_128_GCM,
    AES_256_GCM,
)


class NodeTypeEnum(Enum):
    Shadowsocks = "shadowsocks"
    ShadowsocksR = "shadowsocksr"
    VMess = "vmess"
    VLess = "vless"
    Trojan = "trojan"


XRAY_GITHUB_USER = "XTLS"
XRAY_GITHUB_REPO = "Xray-core"

CIPHER_TYPE_DICT = {
    "none": NONE,
    "unknown": UNKNOWN,
    "aes-128-gcm": AES_128_GCM,
    "aes-256-gcm": AES_256_GCM,
    "aes-128-cfb": AES_128_CFB,
    "aes-256-cfb": AES_256_CFB,
    "chacha20": CHACHA20,
    "chacha20-ietf": CHACHA20_IETF,
    "chacha20-poly1305": CHACHA20_POLY1305,
}

NETWORK_DICT = {"tcp": network_pb2.TCP, "udp": network_pb2.UDP, "raw-tcp": network_pb2.RawTCP}

SSPANEL_NODE_TYPE = {
    0: NodeTypeEnum.Shadowsocks,
    10: NodeTypeEnum.Shadowsocks,
    11: NodeTypeEnum.VMess,
    12: NodeTypeEnum.VMess,
    14: NodeTypeEnum.Trojan,
}
