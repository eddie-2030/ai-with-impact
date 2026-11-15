"""Queries used by the customer service quality dashboard."""

import pandas as pd


DASHBOARD_QUERY = """
SELECT
    c.conv_ext_id,
    c.started_at,
    c.channel,
    c.language,
    a.name AS agent_name,
    s.professionalism AS professionalism_score,
    s.friendliness AS friendliness_score,
    s.resolution_effectiveness AS resolution_effectiveness_score,
    (s.professionalism + s.friendliness + s.resolution_effectiveness) / 3.0
        AS overall_score,
    s.created_at AS scored_at
FROM conversations AS c
JOIN agents AS a ON c.agent_id = a.id
LEFT JOIN scores AS s ON c.id = s.conversation_id
ORDER BY c.started_at DESC
"""


def load_dashboard_data(connection):
    """Load conversation and score columns using the database schema names."""
    return pd.read_sql(DASHBOARD_QUERY, connection)
