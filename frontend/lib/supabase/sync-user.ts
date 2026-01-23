import { SupabaseClient } from '@supabase/supabase-js'

export async function syncUserToDatabase(supabase: SupabaseClient) {
  try {
    // Get the authenticated user
    const { data: { user }, error: userError } = await supabase.auth.getUser()

    if (userError || !user) {
      console.error('Error getting user:', userError)
      return { success: false, error: userError }
    }

    // Extract name from Google metadata
    const fullName = user.user_metadata?.full_name
      || user.user_metadata?.name
      || user.email?.split('@')[0]
      || 'User'

    const email = user.email || ''

    // Upsert user into public.users table
    const { error: upsertError } = await supabase
      .from('users')
      .upsert(
        {
          id: user.id,
          name: fullName,
          email: email,
        },
        {
          onConflict: 'id',
          ignoreDuplicates: false,
        }
      )

    if (upsertError) {
      console.error('Error syncing user to database:', upsertError)
      return { success: false, error: upsertError }
    }

    return { success: true }
  } catch (error) {
    console.error('Unexpected error syncing user:', error)
    return { success: false, error }
  }
}
