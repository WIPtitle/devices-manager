INSERT INTO systemconfig (key, value) VALUES
    ('warning_cooldown_seconds', '60')
ON CONFLICT DO NOTHING;
