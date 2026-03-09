INSERT INTO systemconfig (key, value) VALUES
    ('warning_notification_delay_seconds', '0')
ON CONFLICT DO NOTHING;
