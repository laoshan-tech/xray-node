import asyncio
import json
import logging
from typing import Union

import grpc
import psutil
from google.protobuf import message as _message
from xray_rpc.app.stats.command import command_pb2 as stats_command_pb2
from xray_rpc.app.stats.command import command_pb2_grpc as stats_command_pb2_grpc
from xray_rpc.common.serial import typed_message_pb2

from xray_node.config import Config
from xray_node.core import cfg
from xray_node.utils.install import XrayFile

logger = logging.getLogger(__name__)
cfg_cls = Config()


def to_typed_message(message: _message):
    return typed_message_pb2.TypedMessage(type=message.DESCRIPTOR.full_name, value=message.SerializeToString())


def ip2bytes(ip: str):
    return bytes([int(i) for i in ip.split(".")])


class Xray(object):
    def __init__(self, xray_f: XrayFile):
        self.xray_f = xray_f
        self.xray_proc: Union[None, psutil.Process] = None
        self.xray_client = grpc.insecure_channel(target=f"{cfg_cls.local_api_host}:{cfg_cls.local_api_port}")

    async def get_user_upload_traffic(self, email: str, reset: bool = False) -> Union[int, None]:
        """
        获取用户上行流量，单位字节
        :param email: 邮箱，用于标识用户
        :param reset: 是否重置流量统计
        :return:
        """
        stub = stats_command_pb2_grpc.StatsServiceStub(self.xray_client)
        try:
            return stub.GetStats(
                stats_command_pb2.GetStatsRequest(name=f"user>>>{email}>>>traffic>>>uplink", reset=reset)
            ).stat.value
        except grpc.RpcError:
            return None

    async def get_user_download_traffic(self, email: str, reset: bool = False):
        """
        获取用户下行流量，单位字节
        :param email: 邮箱，用于标识用户
        :param reset: 是否重置流量统计
        :return:
        """
        stub = stats_command_pb2_grpc.StatsServiceStub(self.xray_client)
        try:
            return stub.GetStats(
                stats_command_pb2.GetStatsRequest(name=f"user>>>{email}>>>traffic>>>downlink", reset=reset)
            ).stat.value
        except grpc.RpcError:
            return None

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
            ("04_inbounds.json", cfg.INBOUNDS_CFG),
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
        if self.xray_proc:
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
