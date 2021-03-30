import asyncio
import json
import logging
from typing import Union

import psutil

from xray_node.core import cfg
from xray_node.utils.install import XrayFile

logger = logging.getLogger(__name__)


class Xray(object):
    def __init__(self, xray_f: XrayFile):
        self.xray_f = xray_f
        self.xray_proc: Union[None, psutil.Process] = None

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
