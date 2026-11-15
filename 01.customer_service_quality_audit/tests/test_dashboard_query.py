import sqlite3
import unittest

from dashboard.queries import load_dashboard_data


class DashboardQueryTests(unittest.TestCase):
    def test_loads_scores_from_schema_and_keeps_unscored_conversations(self):
        connection = sqlite3.connect(":memory:")
        connection.executescript(
            """
            CREATE TABLE agents (id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE conversations (
                id INTEGER PRIMARY KEY,
                conv_ext_id TEXT,
                agent_id INTEGER,
                started_at TEXT,
                channel TEXT,
                language TEXT
            );
            CREATE TABLE scores (
                conversation_id INTEGER,
                professionalism REAL,
                friendliness REAL,
                resolution_effectiveness REAL,
                created_at TEXT
            );
            INSERT INTO agents VALUES (1, 'Alex');
            INSERT INTO conversations VALUES
                (1, 'scored', 1, '2026-11-05T09:00:00', 'chat', 'en'),
                (2, 'pending', 1, '2026-11-04T09:00:00', 'call', 'en');
            INSERT INTO scores VALUES
                (1, 4.0, 3.0, 5.0, '2026-11-05T09:01:00');
            """
        )

        try:
            rows = load_dashboard_data(connection)
        finally:
            connection.close()

        self.assertEqual(rows["conv_ext_id"].tolist(), ["scored", "pending"])
        self.assertEqual(rows.loc[0, "friendliness_score"], 3.0)
        self.assertEqual(rows.loc[0, "overall_score"], 4.0)
        self.assertTrue(rows.loc[1, "overall_score"] != rows.loc[1, "overall_score"])


if __name__ == "__main__":
    unittest.main()
