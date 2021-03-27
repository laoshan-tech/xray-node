from pathlib import Path

import pytest

from xray_node.utils import http


class TestHttp(object):
    @pytest.mark.asyncio
    async def test_download(self):
        url = "http://cachefly.cachefly.net/100mb.test"
        target = Path(__file__).parent / "xray_node_download_test.bin"
        assert await http.download(url=url, target=target) is True
        target.unlink()
