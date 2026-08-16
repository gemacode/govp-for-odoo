import json
import urllib.error
import urllib.parse
import urllib.request


class GovpExchangeError(Exception):
    pass


class GovpExchangeClient:
    def __init__(self, base_url, token, timeout=10):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _request(self, path, method="GET", payload=None, idempotency_key=None):
        headers = {"Accept": "application/json", "Authorization": "Bearer %s" % self.token}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        request = urllib.request.Request(
            "%s%s" % (self.base_url, path),
            data=None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise GovpExchangeError("GOVP Exchange HTTP %s: %s" % (error.code, detail[:300])) from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise GovpExchangeError("GOVP Exchange no disponible: %s" % error) from error

    def inspect(self):
        return self._request("/connectors/me")

    def issue(self, payload, idempotency_key):
        return self._request("/connectors/issue", "POST", payload, idempotency_key)

    def verify(self, code):
        return self._request("/govps/%s" % urllib.parse.quote(code, safe=""))
