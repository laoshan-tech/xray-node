import pytest

from xray_node.core.xray import Xray
from xray_node.utils.install import XrayFile


class TestXray(object):
    xray_f = XrayFile()
    xray = Xray(xray_f=xray_f)

    @pytest.mark.asyncio
    async def test_start_xray(self):
        await self.xray.start()
        assert await self.xray.is_running() is True

    @pytest.mark.asyncio
    async def test_stop_xray(self):
        await self.xray.stop()
        assert await self.xray.is_running() is False
