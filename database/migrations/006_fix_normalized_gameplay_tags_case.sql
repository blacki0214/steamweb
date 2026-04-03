-- Migration 006: Fix normalization order for normalized_gameplay_tags
-- 005 applied regex before lower(), which dropped uppercase letters.

UPDATE games g
SET normalized_gameplay_tags = (
  SELECT COALESCE(array_agg(DISTINCT x.tag), '{}')
  FROM (
    -- Correct order: lower() first, then regex cleanup.
    SELECT regexp_replace(lower(trim(t)), '[^a-z0-9 ]', '', 'g') AS tag
    FROM unnest(COALESCE(g.tags, '{}')) AS t

    UNION ALL
    SELECT 'metroidvania' WHERE lower(COALESCE(g.name, '') || ' ' || COALESCE(g.description, '')) LIKE '%metroidvania%'
    UNION ALL
    SELECT 'roguelike' WHERE lower(COALESCE(g.name, '') || ' ' || COALESCE(g.description, '')) LIKE '%roguelike%'
    UNION ALL
    SELECT 'roguelite' WHERE lower(COALESCE(g.name, '') || ' ' || COALESCE(g.description, '')) LIKE '%roguelite%'
    UNION ALL
    SELECT 'souls like' WHERE lower(COALESCE(g.name, '') || ' ' || COALESCE(g.description, '')) LIKE '%souls%'
    UNION ALL
    SELECT 'survival' WHERE lower(COALESCE(g.name, '') || ' ' || COALESCE(g.description, '')) LIKE '%survival%'
    UNION ALL
    SELECT 'strategy' WHERE lower(COALESCE(g.name, '') || ' ' || COALESCE(g.description, '')) LIKE '%strategy%'
    UNION ALL
    SELECT 'simulation' WHERE lower(COALESCE(g.name, '') || ' ' || COALESCE(g.description, '')) LIKE '%simulation%'
    UNION ALL
    SELECT 'cozy' WHERE lower(COALESCE(g.name, '') || ' ' || COALESCE(g.description, '')) LIKE '%cozy%'
    UNION ALL
    SELECT 'platformer' WHERE lower(COALESCE(g.name, '') || ' ' || COALESCE(g.description, '')) LIKE '%platformer%'
    UNION ALL
    SELECT 'puzzle' WHERE lower(COALESCE(g.name, '') || ' ' || COALESCE(g.description, '')) LIKE '%puzzle%'
    UNION ALL
    SELECT 'action rpg' WHERE lower(COALESCE(g.name, '') || ' ' || COALESCE(g.description, '')) LIKE '%action rpg%'
    UNION ALL
    SELECT 'story rich' WHERE lower(COALESCE(g.name, '') || ' ' || COALESCE(g.description, '')) LIKE '%story rich%'
  ) AS x
  WHERE x.tag IS NOT NULL
    AND x.tag <> ''
    AND x.tag NOT IN (
      'single player',
      'multi player',
      'co op',
      'online co op',
      'lan co op',
      'shared split screen',
      'shared split screen co op',
      'cross platform multiplayer',
      'steam achievements',
      'steam trading cards',
      'steam workshop',
      'steam cloud',
      'family sharing',
      'remote play on phone',
      'remote play on tablet',
      'remote play on tv',
      'remote play together',
      'partial controller support',
      'full controller support',
      'tracked controller support',
      'vr supported',
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
