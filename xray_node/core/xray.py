import asyncio
import json
import logging
from typing import Union

import grpc
import psutil
from google.protobuf import message as _message
from xray_rpc.app.proxyman import config_pb2 as proxyman_config_pb2
from xray_rpc.app.proxyman.command import (
    command_pb2_grpc as proxyman_command_pb2_grpc,
    command_pb2 as proxyman_command_pb2,
)
from xray_rpc.app.stats.command import command_pb2 as stats_command_pb2, command_pb2_grpc as stats_command_pb2_grpc
from xray_rpc.common.net import port_pb2, address_pb2
from xray_rpc.common.protocol import user_pb2
from xray_rpc.common.serial import typed_message_pb2
from xray_rpc.core import config_pb2 as core_config_pb2
from xray_rpc.proxy.shadowsocks import config_pb2 as shadowsocks_config_pb2
from xray_rpc.proxy.trojan import config_pb2 as trojan_config_pb2
from xray_rpc.proxy.vless import account_pb2 as vless_account_pb2
from xray_rpc.proxy.vless.inbound import config_pb2 as vless_inbound_config_pb2
from xray_rpc.proxy.vmess import account_pb2 as vmess_account_pb2
from xray_rpc.proxy.vmess.inbound import config_pb2 as vmess_inbound_config_pb2

from xray_node.config import Config
from xray_node.core import cfg
from xray_node.exceptions import EmailExistsError, InboundTagNotFound, XrayError, AddressAlreadyInUseError
from xray_node.utils.consts import NETWORK_DICT
from xray_node.utils.install import XrayFile

logger = logging.getLogger(__name__)


def to_typed_message(message: _message):
    return typed_message_pb2.TypedMessage(type=message.DESCRIPTOR.full_name, value=message.SerializeToString())


def ip2bytes(ip: str):
    return bytes([int(i) for i in ip.split(".")])


class Protocol(object):
    def __init__(self):
        self.message = None


class VMessInbound(Protocol):
    def __init__(self, email: str, level: int, alter_id: int, user_id: str):
        """
        VMess
        :param email: 邮箱
        :param level: 等级
        :param alter_id:
        :param user_id: UUID
        """
        super(VMessInbound, self).__init__()
        self.message = to_typed_message(
            vmess_inbound_config_pb2.Config(
                user=[
                    user_pb2.User(
                        email=email,
                        level=level,
                        account=to_typed_message(vmess_account_pb2.Account(id=user_id, alter_id=alter_id)),
                    )
                ]
            )
        )


class VLESSInbound(Protocol):
    def __init__(self, email: str, level: int, flow: int, user_id: str):
        """
        VLESS
        :param email: 邮箱
        :param level: 等级
        :param flow: flow 如 xtls-rprx-direct
        :param user_id: UUID
        """
        super(VLESSInbound, self).__init__()
        self.message = to_typed_message(
            vless_inbound_config_pb2.Config(
                clients=[
                    user_pb2.User(
                        email=email,
                        level=level,
                        account=to_typed_message(vless_account_pb2.Account(id=user_id, flow=flow)),
                    )
                ],
                decryption="",
                fallbacks=[],
            )
        )


class ShadowsocksInbound(Protocol):
    def __init__(self, email: str, level: int, password: str, cipher_type: int):
        """
        Shadowsocks
        :param email: 邮箱
        :param level: 等级
        :param password: 密码
        :param cipher_type: 加密方式
        """
        super(ShadowsocksInbound, self).__init__()
        self.message = to_typed_message(
            shadowsocks_config_pb2.ServerConfig(
                users=[
                    user_pb2.User(
                        email=email,
                        level=level,
                        account=to_typed_message(
                            shadowsocks_config_pb2.Account(password=password, cipher_type=cipher_type)
                        ),
                    )
                ],
                network=[NETWORK_DICT["tcp"], NETWORK_DICT["udp"]],
            )
        )


class TrojanInbound(Protocol):
    def __init__(self, email: str, level: int, password: str, flow: str):
        """
        Trojan
        :param email: 邮箱
        :param level: 等级
        :param password: 密码
        :param flow: 流控
        """
        super(TrojanInbound, self).__init__()
        self.message = to_typed_message(
            trojan_config_pb2.ServerConfig(
                users=[
                    user_pb2.User(
                        email=email,
                        level=level,
                        account=to_typed_message(trojan_config_pb2.Account(password=password, flow=flow)),
                    )
                ],
                fallbacks=[],
            )
        )


class Xray(object):
    def __init__(self, xray_f: XrayFile):
        self.xray_f = xray_f
        self.xray_proc: Union[None, psutil.Process] = None

        self.config = Config(cfg=self.xray_f.xn_cfg_fn)
        self.xray_client = grpc.insecure_channel(target=f"{self.config.local_api_host}:{self.config.local_api_port}")

    async def get_user_upload_traffic(self, email: str, reset: bool = False) -> Union[int, None]:
        """
        获取用户上行流量，单位字节
        :param email: 邮箱，用于标识用户
        :param reset: 是否重置流量统计
        :return:
        """
        stub = stats_command_pb2_grpc.StatsServiceStub(self.xray_client)
        try:
            resp = stub.GetStats(
                stats_command_pb2.GetStatsRequest(name=f"user>>>{email}>>>traffic>>>uplink", reset=reset)
            )
            return resp.stat.value
        except grpc.RpcError:
            return None

    async def get_user_download_traffic(self, email: str, reset: bool = False) -> Union[int, None]:
        """
        获取用户下行流量，单位字节
        :param email: 邮箱，用于标识用户
        :param reset: 是否重置流量统计
        :return:
        """
        stub = stats_command_pb2_grpc.StatsServiceStub(self.xray_client)
        try:
            resp = stub.GetStats(
                stats_command_pb2.GetStatsRequest(name=f"user>>>{email}>>>traffic>>>downlink", reset=reset)
            )
            return resp.stat.value
        except grpc.RpcError:
            return None

    async def get_inbound_upload_traffic(self, inbound_tag: str, reset: bool = False) -> Union[int, None]:
        """
        获取特定传入连接上行流量，单位字节
        :param inbound_tag:
        :return:
        """
        stub = stats_command_pb2_grpc.StatsServiceStub(self.xray_client)
        try:
            resp = stub.GetStats(
                stats_command_pb2.GetStatsRequest(name=f"inbound>>>{inbound_tag}>>>traffic>>>uplink", reset=reset)
            )
            return resp.stat.value
        except grpc.RpcError:
            return None

    async def get_inbound_download_traffic(self, inbound_tag: str, reset: bool = False) -> Union[int, None]:
        """
        获取特定传入连接下行流量，单位字节
        :param inbound_tag:
        :return:
        """
        stub = stats_command_pb2_grpc.StatsServiceStub(self.xray_client)
        try:
            resp = stub.GetStats(
                stats_command_pb2.GetStatsRequest(name=f"inbound>>>{inbound_tag}>>>traffic>>>downlink", reset=reset)
            )
            return resp.stat.value
        except grpc.RpcError:
            return None

    async def add_user(self, inbound_tag: str, user_id: int, email: str, level: int, type: str, alter_id: str):
        """
        在一个传入连接中添加一个用户
        :param inbound_tag:
        :param user_id:
        :param email:
        :param level:
        :param type:
        :param alter_id:
        :return:
        """
        stub = proxyman_command_pb2_grpc.HandlerServiceStub(self.xray_client)
        try:
            if type == "vmess":
                user = user_pb2.User(
                    email=email,
                    level=level,
                    account=to_typed_message(vmess_account_pb2.Account(id=user_id, alter_id=alter_id)),
                )
            elif type == "vless":
                user = user_pb2.User(
                    email=email,
                    level=level,
                    account=to_typed_message(vless_account_pb2.Account(id=user_id, alter_id=alter_id)),
                )
            elif type == "shadowsocks":
                user = user_pb2.User(
                    email=email, level=level, account=to_typed_message(shadowsocks_config_pb2.Account())
                )
            elif type == "trojan":
                user = user_pb2.User(email=email, level=level, account=to_typed_message(trojan_config_pb2.Account()))
            else:
                raise XrayError(f"不支持的传入连接类型 {type}")

            stub.AlterInbound(
                proxyman_command_pb2.AlterInboundRequest(
                    tag=inbound_tag,
                    operation=to_typed_message(proxyman_command_pb2.AddUserOperation(user=user)),
                )
            )
            return user_id
        except grpc.RpcError as rpc_err:
            detail = rpc_err.details()
            if detail.endswith(f"User {email} already exists."):
                raise EmailExistsError(detail, email)
            elif detail.endswith(f"handler not found: {inbound_tag}"):
                raise InboundTagNotFound(detail, inbound_tag)
            else:
                raise XrayError(detail)

    async def remove_user(self, inbound_tag: str, email: str):
        """
        在一个传入连接中删除一个用户
        :param inbound_tag:
        :param email:
        :return:
        """
        stub = proxyman_command_pb2_grpc.HandlerServiceStub(self.xray_client)
        try:
            stub.AlterInbound(
                proxyman_command_pb2.AlterInboundRequest(
                    tag=inbound_tag, operation=to_typed_message(proxyman_command_pb2.RemoveUserOperation(email=email))
                )
            )
        except grpc.RpcError as rpc_err:
            detail = rpc_err.details()
            if detail.endswith(f"User {email} already exists."):
                raise EmailExistsError(detail, email)
            elif detail.endswith(f"handler not found: {inbound_tag}"):
                raise InboundTagNotFound(detail, inbound_tag)
            else:
                raise XrayError(detail)

    async def add_inbound(self, inbound_tag: str, address: str, port: int, protocol: Protocol) -> None:
        """
        增加传入连接
        :param inbound_tag: 传入连接的标识
        :param address: 监听地址
        :param port: 监听端口
        :param protocol: 代理配置
        """
        stub = proxyman_command_pb2_grpc.HandlerServiceStub(self.xray_client)
        try:
            logger.error(stub)
            resp = stub.AddInbound(
                proxyman_command_pb2.AddInboundRequest(
                    inbound=core_config_pb2.InboundHandlerConfig(
                        tag=inbound_tag,
                        receiver_settings=to_typed_message(
                            proxyman_config_pb2.ReceiverConfig(
                                port_range=port_pb2.PortRange(
                                    From=port,
                                    To=port,
                                ),
                                listen=address_pb2.IPOrDomain(
                                    ip=ip2bytes(address),  # 4字节或16字节
                                ),
                                allocation_strategy=None,
                                stream_settings=None,
                                receive_original_destination=None,
                                domain_override=None,
                                sniffing_settings=None,
                            )
                        ),
                        proxy_settings=protocol.message,
                    )
                )
            )
            logger.error(resp)
        except grpc.RpcError as rpc_err:
            detail = rpc_err.details()
            if detail.endswith("address already in use"):
                raise AddressAlreadyInUseError(detail, port)
            else:
                raise XrayError(detail)

    async def remove_inbound(self, inbound_tag: str):
        """
        删除传入连接
        :param inbound_tag:
        :return:
        """
        stub = proxyman_command_pb2_grpc.HandlerServiceStub(self.xray_client)
        try:
            stub.RemoveInbound(proxyman_command_pb2.RemoveInboundRequest(tag=inbound_tag))
        except grpc.RpcError as rpc_err:
            detail = rpc_err.details()
            if detail == "not enough information for making a decision":
                raise InboundTagNotFound(detail, inbound_tag)
            else:
                raise XrayError(detail)

    async def gen_cfg(self) -> None:
        """
        生成基础配置文件
        :return:
        """
        default_cfgs = [
            ("00_base.json", cfg.BASE_CFG),
            ("01_api.json", cfg.API_CFG),
            ("02_policy.json", cfg.POLICY_CFG),
            ("03_routing.json", cfg.ROUTING_CFG),
            ("04_inbounds.json", cfg.get_inbound_cfg(cfg_cls=self.config)),
            ("05_outbounds.json", cfg.OUTBOUNDS_CFG),
        ]

        for fn, content in default_cfgs:
            p = self.xray_f.xray_conf_dir / fn
            if not p.exists():
                with open(p, "w") as f:
                    json.dump(content, f, indent=2)

    async def is_running(self) -> bool:
        """
        检查xray-core运行
        :return:
        """
        return psutil.pid_exists(self.xray_proc.pid)

    async def start(self) -> None:
        """
        启动xray-core
        :return:
        """
        await self.gen_cfg()
        self.xray_proc = await asyncio.create_subprocess_exec(
            self.xray_f.xray_exe_fn,
            "run",
            "-confdir",
            self.xray_f.xray_conf_dir,
            stdout=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.sleep(0.5)
        if await self.is_running() is True:
            logger.info(f"xray-core 启动成功")
        else:
            self.xray_proc = None
            logger.warning(f"xray-core 启动失败")

    async def stop(self) -> None:
        """
        停止xray-core
        :return:
        """
        if self.xray_proc and await self.is_running():
            self.xray_proc.terminate()
        else:
            return

        await asyncio.sleep(0.5)
        if await self.is_running():
            logger.warning(f"xray-core 进程 {self.xray_proc.pid} 仍在运行，尝试 kill")
            self.xray_proc.kill()
        else:
            logger.info(f"xray-core 进程 {self.xray_proc.pid} 已停止运行")
            return

        await asyncio.sleep(0.5)
        if await self.is_running():
            logger.error(f"xray-core 进程 {self.xray_proc.pid} 仍在运行，kill 失败，需要手动处理")
        else:
            logger.info(f"xray-core 进程 {self.xray_proc.pid} 已停止运行")
            return
