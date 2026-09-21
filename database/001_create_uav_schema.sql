BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS uav;

-- Legacy tables copied from SCM_webgis are renamed after import:
--   uav.reference_zones          <- public.zone
--   uav.field_access_constraints <- public.restricted_area
-- They are reference layers only, not ground truth for GA road accessibility.

CREATE TABLE IF NOT EXISTS uav.survey_projects (
    project_id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS uav.survey_areas (
    area_id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES uav.survey_projects(project_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    source_file TEXT,
    geom geometry(MultiPolygon, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS uav.road_networks (
    road_id BIGSERIAL PRIMARY KEY,
    area_id BIGINT REFERENCES uav.survey_areas(area_id) ON DELETE CASCADE,
    name TEXT,
    source_file TEXT,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    geom geometry(MultiLineString, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS uav.airspace_zones (
    airspace_id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    zone_type TEXT NOT NULL CHECK (zone_type IN ('prohibited', 'restricted')),
    source_file TEXT NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    geom geometry(MultiPolygon, 4326) NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (name, zone_type, source_file)
);

CREATE TABLE IF NOT EXISTS uav.optimization_runs (
    run_id BIGSERIAL PRIMARY KEY,
    area_id BIGINT NOT NULL REFERENCES uav.survey_areas(area_id) ON DELETE CASCADE,
    algorithm TEXT NOT NULL DEFAULT 'genetic_algorithm',
    parameters JSONB NOT NULL,
    metrics JSONB,
    candidate_count INTEGER,
    status TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('queued', 'running', 'completed', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS uav.control_points (
    point_id BIGSERIAL PRIMARY KEY,
    area_id BIGINT NOT NULL REFERENCES uav.survey_areas(area_id) ON DELETE CASCADE,
    run_id BIGINT REFERENCES uav.optimization_runs(run_id) ON DELETE CASCADE,
    point_type TEXT NOT NULL CHECK (point_type IN ('gcp', 'check_point', 'candidate')),
    point_name TEXT,
    is_selected BOOLEAN NOT NULL DEFAULT TRUE,
    visit_order INTEGER,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    geom geometry(Point, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS uav.survey_routes (
    route_id BIGSERIAL PRIMARY KEY,
    run_id BIGINT REFERENCES uav.optimization_runs(run_id) ON DELETE CASCADE,
    name TEXT NOT NULL DEFAULT 'Survey route',
    distance_m NUMERIC(12, 2),
    stops INTEGER,
    geom geometry(LineString, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS survey_areas_geom_idx ON uav.survey_areas USING GIST (geom);
CREATE INDEX IF NOT EXISTS road_networks_geom_idx ON uav.road_networks USING GIST (geom);
CREATE INDEX IF NOT EXISTS airspace_zones_geom_idx ON uav.airspace_zones USING GIST (geom);
CREATE INDEX IF NOT EXISTS control_points_geom_idx ON uav.control_points USING GIST (geom);
CREATE INDEX IF NOT EXISTS survey_routes_geom_idx ON uav.survey_routes USING GIST (geom);

COMMIT;
