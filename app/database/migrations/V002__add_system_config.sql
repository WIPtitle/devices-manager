CREATE TABLE IF NOT EXISTS systemconfig (
    key VARCHAR PRIMARY KEY,
    value VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS gpioserver (
    id SERIAL PRIMARY KEY,
    url VARCHAR UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS mp3server (
    id SERIAL PRIMARY KEY,
    url VARCHAR UNIQUE NOT NULL,
    audio_type_alarm BOOLEAN DEFAULT TRUE,
    audio_type_waiting BOOLEAN DEFAULT TRUE,
    audio_type_warning BOOLEAN DEFAULT TRUE
);

INSERT INTO systemconfig (key, value) VALUES
    ('alarm_recording_duration_seconds', '120'),
    ('always_recording_duration_seconds', '3600'),
    ('warning_cooldown_seconds', '60'),
    ('detection_yolo_model', 'yolo26n'),
    ('detection_fps', '0.5'),
    ('detection_frame_width', '640'),
    ('detection_frame_height', '360'),
    ('detection_confidence', '50'),
    ('motion_sensitivity', '50'),
    ('timezone', 'Europe/Rome')
ON CONFLICT DO NOTHING;
