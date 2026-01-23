import { createClient } from '@/lib/supabase/server'
import { NextResponse } from 'next/server'
import { syncUserToDatabase } from '@/lib/supabase/sync-user'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const code = searchParams.get('code')
  const next = searchParams.get('next') ?? '/dashboard'

  if (code) {
    const supabase = await createClient()
    const { error } = await supabase.auth.exchangeCodeForSession(code)

    if (!error) {
      // Sync user to database (non-blocking)
      await syncUserToDatabase(supabase)

      return NextResponse.redirect(new URL(next, request.url))
    }
  }

  // Return to home if error
  return NextResponse.redirect(new URL('/', request.url))
}
