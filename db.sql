CREATE TABLE approved_fragmentation (
    id SERIAL PRIMARY KEY,
    image_id int,
    drawpoint_name VARCHAR(255)  NULL,
    new_fine_area REAL,
    new_small_area REAL,
    new_medium_area REAL,
    new_large_area REAL,
    new_oversized_area REAL,
    dp_condition SMALLINT,
    bund VARCHAR(3),
    wetness SMALLINT,
    drawpointConditionComment  VARCHAR(1000)  NULL,
    fragmentationComment VARCHAR(1000)  NULL,
    wetnessComment VARCHAR(1000)  NULL,
    username VARCHAR(500),
    submitted_date TIMESTAMP WITHOUT TIME ZONE NULL,
    created_date TIMESTAMP WITHOUT TIME ZONE NULL
);

CREATE TABLE fragmentation_images (
    id SERIAL PRIMARY KEY,
    drawpoint_name VARCHAR(255) NOT NULL,
    edited_dp_name VARCHAR(255)  NULL,
    fine_area REAL DEFAULT 0,
    small_area REAL DEFAULT 0,
    medium_area REAL DEFAULT 0,
    large_area REAL DEFAULT 0,
    oversized_area REAL DEFAULT 0,
    raw_image_path VARCHAR(500) NOT NULL,
    predicted_image_path VARCHAR(500) NULL,
    bbox_image_path VARCHAR(500),
    has_bund VARCHAR(3),
    image_status VARCHAR(20),
    is_edited VARCHAR(3),
    imagetaken_date TIMESTAMP WITHOUT TIME ZONE NULL,
    created_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    updated_date TIMESTAMP WITHOUT TIME ZONE  NULL
);