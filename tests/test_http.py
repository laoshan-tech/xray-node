from pathlib import Path

import pytest

from xray_node.utils import http


class TestHttp(object):
    @pytest.mark.asyncio
    async def test_download(self):
        url = "https://cdn.jsdelivr.net/gh/jquery/jquery/dist/jquery.min.js"
        target = Path(__file__).parent / "download.test"
        assert await http.download(url=url, target=target) is True
        target.unlink()
