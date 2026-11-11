CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE TABLE IF NOT EXISTS reservations (
    reservation_id UUID PRIMARY KEY,
    environment_id UUID NOT NULL,
    requester VARCHAR(200) NOT NULL,
    purpose TEXT NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'CONFIRMED' CHECK (status IN ('CONFIRMED', 'CANCELLED', 'COMPLETED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT valid_reservation_period CHECK (start_time < end_time),
    CONSTRAINT no_confirmed_overlap EXCLUDE USING gist (
        environment_id WITH =,
        tstzrange(start_time, end_time, '[)') WITH &&
    ) WHERE (status = 'CONFIRMED')
);
CREATE INDEX IF NOT EXISTS reservations_requester_idx
    ON reservations (requester, start_time DESC);
