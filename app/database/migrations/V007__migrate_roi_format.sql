-- Migrate detection_roi from single polygon format [[x,y],[x,y],...] to array of polygons [[[x,y],[x,y],...]]
-- Old format starts with "[[0" (single polygon), new format starts with "[[[" (array of polygons)
UPDATE camera
SET detection_roi = '[' || detection_roi || ']'
WHERE detection_roi IS NOT NULL
  AND detection_roi NOT LIKE '[[[%';
