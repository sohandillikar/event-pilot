CREATE TABLE public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT NOT NULL UNIQUE,
    company TEXT NOT NULL
);

CREATE TABLE public.events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    number_of_attendees INTEGER NOT NULL,
    venue_type TEXT NOT NULL CHECK (venue_type IN ('hotel', 'resort', 'restaurant', 'bar', 'nightclub', 'event space')),
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    budget_min INTEGER NOT NULL,
    budget_max INTEGER NOT NULL,
    required_amenities JSONB NOT NULL DEFAULT '[]'::jsonb,
    additional_details JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE public.venues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_id UUID NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    google_place_id TEXT NOT NULL,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    phone TEXT NOT NULL,
    website TEXT NOT NULL,
    rating NUMERIC,
    rating_count INTEGER,
    latitude NUMERIC NOT NULL,
    longitude NUMERIC NOT NULL,
    google_types JSONB NOT NULL DEFAULT '[]'::jsonb,
    pricing TEXT,
    status TEXT NOT NULL DEFAULT 'discovered' CHECK (status IN ('discovered', 'contacted', 'negotiated', 'selected', 'rejected'))
);

CREATE TABLE public.email_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_id UUID NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    resend_id TEXT UNIQUE NOT NULL,
    from_email TEXT NOT NULL,
    to_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    body_text TEXT,
    body_html TEXT
);