CREATE TABLE IF NOT EXISTS movies (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    submitted_by VARCHAR(100) DEFAULT 'anonymous',
    round_added INTEGER DEFAULT 1,
    tmdb_id INTEGER,
    poster_url VARCHAR(500),
    rating FLOAT,
    age_rating VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rounds (
    id SERIAL PRIMARY KEY,
    round_number INTEGER UNIQUE NOT NULL,
    phase VARCHAR(20) NOT NULL DEFAULT 'submission',
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS votes (
    id SERIAL PRIMARY KEY,
    movie_id INTEGER REFERENCES movies(id) ON DELETE CASCADE,
    round_number INTEGER NOT NULL,
    visitor_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(round_number, visitor_id)
);

CREATE TABLE IF NOT EXISTS results (
    id SERIAL PRIMARY KEY,
    round_number INTEGER NOT NULL,
    movie_id INTEGER REFERENCES movies(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(round_number, position)
);

INSERT INTO rounds (round_number, phase, is_active) VALUES
    (1, 'submission', TRUE),
    (2, 'pending', FALSE),
    (3, 'pending', FALSE)
ON CONFLICT (round_number) DO NOTHING;
