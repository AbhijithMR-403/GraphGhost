-- video_file held only the file name; store the path relative to the project root.
ALTER TABLE reels RENAME COLUMN video_file TO video_path;
UPDATE reels SET video_path = 'downloads/' || video_path
WHERE video_path IS NOT NULL AND video_path NOT LIKE '%/%';
