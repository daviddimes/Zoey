import os
import unittest

from health import (
    build_google_health_auth_url,
    build_health_dashboard,
    is_health_connected,
    mark_health_connected,
    parse_health_callback_params,
    fetch_health_metrics,
)


class HealthTests(unittest.TestCase):
    def test_build_health_dashboard_includes_key_sections(self):
        dashboard = build_health_dashboard()

        self.assertIn('Health Dashboard', dashboard)
        self.assertIn('Steps', dashboard)
        self.assertIn('Heart Rate', dashboard)
        self.assertIn('Sleep', dashboard)
        self.assertIn('Calories', dashboard)

    def test_build_google_health_auth_url_contains_expected_values(self):
        url = build_google_health_auth_url('12345')

        self.assertIn('accounts.google.com/o/oauth2/auth', url)
        self.assertIn('client_id=', url)
        self.assertIn('state=12345', url)

    def test_mark_health_connected_persists_user(self):
        connection_file = os.path.join(os.path.dirname(__file__), '..', 'health_connections.json')
        if os.path.exists(connection_file):
            os.remove(connection_file)

        self.assertTrue(mark_health_connected(999))
        self.assertTrue(is_health_connected(999))

        if os.path.exists(connection_file):
            os.remove(connection_file)

    def test_parse_health_callback_params_extracts_code_and_state(self):
        params = parse_health_callback_params('code=abc123&state=456')

        self.assertEqual(params['code'], 'abc123')
        self.assertEqual(params['state'], '456')

    def test_fetch_health_metrics_returns_dict_with_required_keys(self):
        metrics = fetch_health_metrics(None)
        
        self.assertIsInstance(metrics, dict)
        self.assertIn('steps', metrics)
        self.assertIn('heart_rate', metrics)
        self.assertIn('sleep_hours', metrics)
        self.assertIn('calories', metrics)


if __name__ == '__main__':
    unittest.main()
