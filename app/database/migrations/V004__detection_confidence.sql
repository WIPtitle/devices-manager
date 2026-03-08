DELETE FROM systemconfig WHERE key IN ('detection_fps', 'detection_frame_width', 'detection_frame_height');

INSERT INTO systemconfig (key, value) VALUES
    ('detection_confidence', '50'),
    ('motion_sensitivity', '50')
ON CONFLICT DO NOTHING;
