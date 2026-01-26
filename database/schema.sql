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
    status TEXT NOT NULL DEFAULT 'discovered' CHECK (status IN ('discovered', 'negotiating', 'negotiated', 'selected', 'rejected')),
    UNIQUE(event_id, google_place_id)
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

CREATE TABLE public.negotiations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_id UUID NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    venue_id UUID NOT NULL REFERENCES public.venues(id) ON DELETE CASCADE,
    vapi_call_id TEXT NOT NULL,
    
    -- Negotiation data
    venue_initial_quote INTEGER,  -- First price they give
    venue_initial_quote_breakdown JSONB,  -- e.g. {"room": 3000, "catering": 2000, "av": 500}
    
    customer_budget_max INTEGER NOT NULL,  -- Snapshot from event at time of call
    
    agent_counteroffer INTEGER,  -- What your agent offered
    agent_counteroffer_breakdown JSONB,  -- e.g. {"room": 3000, "catering": 2000, "av": 500}
    agent_counteroffer_reasoning TEXT,  -- Why this amount (optional)
    
    venue_final_quote INTEGER,  -- Final price if they moved
    venue_final_quote_breakdown JSONB,  -- e.g. {"room": 3000, "catering": 2000, "av": 500}

    -- Additional context
    venue_contact_person TEXT,  -- Who did we speak with?
    venue_availability TEXT CHECK (venue_availability IN ('available', 'tentatively_available', 'not_available')),
    venue_flexibility TEXT CHECK (venue_flexibility IN ('flexible', 'semi_flexible', 'not_flexible')),
    restrictions JSONB DEFAULT '[]'::jsonb,  -- Any limitations they mentioned
    notes TEXT
);