from datetime import datetime
from unittest.mock import patch

from django.db import DatabaseError
from django.test import Client, TestCase
from django.urls import reverse


class HealthCheckTests(TestCase):
    """Test suite for the system health check endpoints."""

    def setUp(self):
        self.client = Client()

    def test_health_endpoint_success(self):
        """GET /health/ should return status ok, timestamp, and connected database."""
        response = self.client.get(reverse("health_check"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        data = response.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("database"), "connected")
        self.assertIn("timestamp", data)

        # Validate that the timestamp is a valid ISO-8601 string
        parsed_time = datetime.fromisoformat(data["timestamp"])
        self.assertIsNotNone(parsed_time)

    def test_api_health_endpoint_success(self):
        """GET /api/health/ should return status ok, timestamp, and connected database."""
        response = self.client.get(reverse("api_health_check"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        data = response.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("database"), "connected")
        self.assertIn("timestamp", data)

        parsed_time = datetime.fromisoformat(data["timestamp"])
        self.assertIsNotNone(parsed_time)

    def test_direct_url_paths_match(self):
        """Direct URL requests to /health/ and /api/health/ should succeed."""
        for path in ["/health/", "/api/health/"]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data.get("status"), "ok")
                self.assertEqual(data.get("database"), "connected")

    @patch("django.db.connection.cursor")
    def test_health_endpoint_database_error(self, mock_cursor):
        """Database connection failure should return 503 Service Unavailable and status error."""
        mock_cursor.side_effect = DatabaseError("Database connection refused")

        for route_name in ["health_check", "api_health_check"]:
            with self.subTest(route=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response["Content-Type"], "application/json")

                data = response.json()
                self.assertEqual(data.get("status"), "error")
                self.assertEqual(data.get("database"), "disconnected")
                self.assertIn("timestamp", data)
                parsed_time = datetime.fromisoformat(data["timestamp"])
                self.assertIsNotNone(parsed_time)

    @patch("django.db.connection.cursor")
    def test_health_endpoint_generic_exception(self, mock_cursor):
        """Unexpected connection failure should return 503 Service Unavailable and status error."""
        mock_cursor.side_effect = RuntimeError("Unexpected operational failure")

        for route_name in ["health_check", "api_health_check"]:
            with self.subTest(route=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response["Content-Type"], "application/json")

                data = response.json()
                self.assertEqual(data.get("status"), "error")
                self.assertEqual(data.get("database"), "error")
                self.assertIn("timestamp", data)
                parsed_time = datetime.fromisoformat(data["timestamp"])
                self.assertIsNotNone(parsed_time)
