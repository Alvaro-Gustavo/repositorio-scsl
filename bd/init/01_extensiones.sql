-- ============================================================
-- REPOSITORIO SCSL - Base de datos repositorio_scsl
-- Paso 1 de 6: extensiones y funciones de apoyo.
--
-- Docker ejecuta los archivos de bd/init en orden alfabetico,
-- UNA sola vez: cuando crea la base por primera vez.
-- ============================================================
SET client_min_messages = warning;

CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- UUID aleatorios y bcrypt (crypt)
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- busqueda parcial y valores parecidos
CREATE EXTENSION IF NOT EXISTS unaccent;   -- quitar tildes

-- unaccent() no es IMMUTABLE y las columnas calculadas lo exigen.
-- Es seguro fijarlo: el diccionario de tildes no cambia.
CREATE FUNCTION unaccent_inmutable(text) RETURNS text AS $$
    SELECT public.unaccent('public.unaccent'::regdictionary, $1)
$$ LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT;

-- Forma unica de un nombre para compararlo:
-- "Gob. Autónomo  de La Paz" -> "gob. autonomo de la paz"
-- Lleva "public." porque pg_restore trabaja con search_path vacio: sin el
-- esquema, los respaldos no se pueden restaurar (columnas e indices la usan).
CREATE FUNCTION normalizar_texto(text) RETURNS text AS $$
    SELECT regexp_replace(public.unaccent_inmutable(lower(btrim($1))), '\s+', ' ', 'g')
$$ LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT;

-- Busqueda de texto en espanol que ignora tildes:
-- "contratacion" encuentra "contratación".
CREATE TEXT SEARCH CONFIGURATION es_legal (COPY = pg_catalog.spanish);
ALTER TEXT SEARCH CONFIGURATION es_legal
    ALTER MAPPING FOR hword, hword_part, word WITH unaccent, spanish_stem;
