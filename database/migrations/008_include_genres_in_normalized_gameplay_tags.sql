-- Migration 008: include games.genres in normalized_gameplay_tags
-- Keeps system DB-driven while improving genre hit-rate/autocomplete.

UPDATE games g
SET normalized_gameplay_tags = (
  SELECT COALESCE(array_agg(DISTINCT x.tag), '{}')
  FROM (
    SELECT regexp_replace(lower(trim(t)), '[^a-z0-9 ]', '', 'g') AS tag
    FROM unnest(COALESCE(g.tags, '{}')) AS t

    UNION ALL

    SELECT regexp_replace(lower(trim(gen)), '[^a-z0-9 ]', '', 'g') AS tag
    FROM unnest(COALESCE(g.genres, '{}')) AS gen
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
      'shared split screen pvp',
      'cross platform multiplayer',
      'crossplatform multiplayer',
      'online pvp',
      'pvp',
      'lan pvp',
      'mmo',
      'inapp purchases',
      'surround sound',
      'hdr available',
      'captions available',
      'keyboard only option',
      'chat speechtotext',
      'chat texttospeech',
      'steam achievements',
      'steamachievements',
      'steam trading cards',
      'steamtrading cards',
      'steam workshop',
      'steamworkshop',
      'steam cloud',
      'steamcloud',
      'steam leaderboards',
      'steam timeline',
      'steamvr collectibles',
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
      'vr support',
      'includes level editor',
      'includes source sdk',
      'camera comfort',
      'adjustable text size',
      'adjustable difficulty',
      'custom volume controls',
      'mouse only option',
      'touch only option',
      'subtitle options',
      'narrated game menus',
      'commentary available',
      'stereo sound',
      'save anytime',
      'playable without timed input',
      'color alternatives',
      'stats',
      'valve anti cheat enabled',
      'valve anticheat enabled'
    )
);
