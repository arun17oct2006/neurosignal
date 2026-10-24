
import unittest
from unittest.mock import Mock, patch

import httpx

from market_cache import MarketCacheClient, MarketCacheError


class MarketCacheClientTests(unittest.TestCase):
    @patch("market_cache.httpx.post")
    def test_action_sends_action_payload_and_api_key(self, post):
        response = Mock()
        response.json.return_value = {
            "ok": True,
            "cache_key": "US:MSFT:QUOTE",
            "cache_hit": True,
        }
        post.return_value = response

        client = MarketCacheClient(
            "https://cache.example/dev/v1/",
            "test-key",
        )
        result = client.action(
            "cache_get",
            symbol="MSFT",
            cache_key="US:MSFT:QUOTE",
        )

        self.assertEqual(result["ok"], True)
        post.assert_called_once_with(
            "https://cache.example/dev/v1",
            json={
                "action": "cache_get",
                "symbol": "MSFT",
                "cache_key": "US:MSFT:QUOTE",
            },
            headers={"x-api-key": "test-key"},
            timeout=8.0,
        )

    def test_action_requires_both_environment_values(self):
        with self.assertRaisesRegex(
            MarketCacheError,
            "must both be configured",
        ):
            MarketCacheClient("", "").action(
                "get_preferences",
                user_id="user-1",
            )

    def test_action_requires_https(self):
        with self.assertRaisesRegex(
            MarketCacheError,
            "must be an HTTPS URL",
        ):
            MarketCacheClient(
                "http://cache.example/dev/v1",
                "test-key",
            ).action("cache_get", symbol="AAPL")

    @patch("market_cache.httpx.post")
    def test_action_wraps_connection_failures_without_key(self, post):
        post.side_effect = httpx.ConnectError("private request details")

        client = MarketCacheClient(
            "https://cache.example/dev/v1",
            "secret-key",
        )

        with self.assertRaisesRegex(
            MarketCacheError,
            "cache_get' failed",
        ) as error:
            client.action("cache_get", symbol="AAPL")

        self.assertNotIn("secret-key", str(error.exception))
        self.assertNotIn(
            "private request details",
            str(error.exception),
        )

    @patch("market_cache.httpx.post")
    def test_action_includes_http_status_and_response_body(self, post):
        request = httpx.Request(
            "POST",
            "https://cache.example/dev/v1",
        )
        response = httpx.Response(
            400,
            text='{"ok": false, "message": "symbol is required"}',
            request=request,
        )
        post.return_value = response

        client = MarketCacheClient(
            "https://cache.example/dev/v1",
            "secret-key",
        )

        with self.assertRaises(MarketCacheError) as error:
            client.action("cache_get", ticker="AAPL")

        message = str(error.exception)
        self.assertIn("HTTP 400", message)
        self.assertIn("symbol is required", message)
        self.assertNotIn("secret-key", message)

    @patch("market_cache.httpx.post")
    def test_action_rejects_non_object_responses(self, post):
        response = Mock()
        response.json.return_value = []
        post.return_value = response

        client = MarketCacheClient(
            "https://cache.example/dev/v1",
            "test-key",
        )

        with self.assertRaisesRegex(
            MarketCacheError,
            "non-object response",
        ):
            client.action("cache_get", symbol="AAPL")

    @patch("market_cache.httpx.post")
    def test_action_rejects_invalid_json(self, post):
        response = Mock()
        response.json.side_effect = ValueError("invalid JSON")
        post.return_value = response

        client = MarketCacheClient(
            "https://cache.example/dev/v1",
            "test-key",
        )

        with self.assertRaisesRegex(
            MarketCacheError,
            "returned invalid JSON",
        ):
            client.action("cache_get", symbol="AAPL")


if __name__ == "__main__":
    unittest.main()
