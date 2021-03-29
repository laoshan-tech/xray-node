import logging
from pathlib import Path

import httpx

client = httpx.AsyncClient(timeout=httpx.Timeout(timeout=10, connect=15))
logger = logging.getLogger(__name__)


async def download(url: str, target: Path) -> bool:
    """
    下载文件
    :param url:
    :param target: 保存文件路径
    :return: 是否成功
    """
    with open(target, "wb") as f:
        try:
            async with client.stream(method="GET", url=url) as resp:
                logger.info(f"下载 {url} 开始......")
                async for chunk in resp.aiter_bytes():
                    f.write(chunk)

            logger.info(f"从 {url} 下载文件到 {target} 成功")
            return True
        except Exception as e:
            logger.error(f"从 {url} 下载文件到 {target} 失败，{e}")
            return False
