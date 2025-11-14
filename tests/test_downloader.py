import pytest

from pathlib import Path

from arxiv_agent.downloader import download_pdf


class FakeResponse:
    def __init__(self, data: bytes):
        self._data = data

    async def aiter_bytes(self, chunk_size: int = 8192):
        # yield content in two chunks
        mid = max(1, len(self._data) // 2)
        yield self._data[:mid]
        yield self._data[mid:]

    def raise_for_status(self):
        return None


class DummyClient:
    def __init__(self, data: bytes):
        self._data = data

    async def get(self, url, follow_redirects=True):
        return FakeResponse(self._data)

    async def aclose(self):
        return None


@pytest.mark.asyncio
async def test_download_pdf(tmp_path: Path):
    data = b"%PDF-1.4 FAKEPDFCONTENT"
    dest = tmp_path / "test.pdf"
    client = DummyClient(data)

    result = await download_pdf("http://example.com/test.pdf", dest, client=client)
    assert result.exists()
    assert dest.read_bytes() == data


@pytest.mark.asyncio
async def test_download_pdf_retries(tmp_path: Path):
    # Client that fails the first call then succeeds
    class FlakyClient:
        def __init__(self, data: bytes):
            self._data = data
            self.calls = 0

        async def get(self, url, follow_redirects=True):
            self.calls += 1
            if self.calls == 1:
                raise Exception("transient network error")
            return FakeResponse(self._data)

        async def aclose(self):
            return None

    data = b"%PDF-1.4 FAKEPDFCONTENT"
    dest = tmp_path / "test_retry.pdf"
    client = FlakyClient(data)

    result = await download_pdf("http://example.com/test_retry.pdf", dest, client=client)
    assert result.exists()
    assert dest.read_bytes() == data
    assert client.calls >= 2
