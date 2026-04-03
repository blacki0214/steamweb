-- Migration 007: Use tags-only normalization for normalized_gameplay_tags
-- Removes derived keyword injection from title/description and relies strictly on games.tags.

UPDATE games g
SET normalized_gameplay_tags = (
  SELECT COALESCE(array_agg(DISTINCT x.tag), '{}')
  FROM (
    SELECT regexp_replace(lower(trim(t)), '[^a-z0-9 ]', '', 'g') AS tag
    FROM unnest(COALESCE(g.tags, '{}')) AS t
  ) AS x
  WHERE x.tag IS NOT NULL
    AND x.tag <> ''
    AND x.tag NOT IN (
      'single player',
      'singleplayer',
      'multi player',
      'multiplayer',
      'co op',
      'coop',
      'online co op',
      'online coop',
      'lan co op',
      'lan coop',
      'shared split screen',
      'sharedsplit screen',
      'shared split screen co op',
      'sharedsplit screen coop',
      'cross platform multiplayer',
      'crossplatform multiplayer',
      'steam achievements',
      'steamachievements',
      'steam trading cards',
      'steamtrading cards',
      'steam workshop',
      'steamworkshop',
      'steam cloud',
      'steamcloud',
      'family sharing',
      'familysharing',
      'remote play on phone',
      'remoteplay on phone',
      'remote play on tablet',
      'remoteplay on tablet',
      'remote play on tv',
      'remoteplay on tv',
      'remote play together',
      'remoteplay together',
      'partial controller support',
      'full controller support',
      'tracked controller support',
      'vr supported',
      'includes level editor',
      'camera comfort',
      'adjustable text size',
      'adjustable difficulty',
      'custom volume controls',
      'mouse only option',
      'touch only option',
      'subtitle options',
      'stereo sound',
      'save anytime',
      'playable without timed input',
      'color alternatives',
      'stats',
      'valve anti cheat enabled'
    )
);
