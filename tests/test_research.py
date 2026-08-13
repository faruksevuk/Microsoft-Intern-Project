import research


def test_public_url_filter_rejects_local_and_non_http_urls():
    assert not research._safe_public_url("file:///etc/passwd")
    assert not research._safe_public_url("http://localhost:8000")
    assert not research._safe_public_url("http://127.0.0.1")


def test_fetch_rejects_private_redirect_before_request(monkeypatch):
    calls = []

    class Response:
        has_redirect_location = True
        headers = {"Location": "http://127.0.0.1/private"}

        class url:
            @staticmethod
            def join(location):
                return location

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def get(self, url):
            calls.append(url)
            return Response()

    monkeypatch.setattr(research, "_client", lambda: Client())
    monkeypatch.setattr(research, "_safe_public_url", lambda url: url == "https://public.example/start")
    try:
        research.fetch_url("https://public.example/start")
    except ValueError as ex:
        assert "non-public" in str(ex)
    else:
        raise AssertionError("private redirect was accepted")
    assert calls == ["https://public.example/start"]
