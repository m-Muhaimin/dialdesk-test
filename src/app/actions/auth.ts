'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { z } from 'zod';
import { getAppUrl } from '@/lib/env';
import { safeNext } from '@/lib/business';
import { supabaseServer } from '@/lib/supabase/server';

const creds = z.object({ email: z.string().trim().email().max(200), password: z.string().min(8, 'Password must be at least 8 characters').max(200) });
const profileSchema = z.object({
  fullName: z.string().trim().min(1, 'Enter your name').max(80, 'Name must be 80 characters or fewer'),
});
const go = (path: string, key: 'error' | 'notice' | 'saved', msg: string): never => redirect(`${path}?${key}=${encodeURIComponent(msg)}`);

export async function login(form: FormData) {
  const p = creds.safeParse({ email: form.get('email'), password: form.get('password') });
  if (!p.success) go('/login', 'error', p.error.issues[0]?.message ?? 'Check your details');
  const supabase = await supabaseServer();
  const { error } = await supabase.auth.signInWithPassword(p.data!);
  if (error) go('/login', 'error', 'Incorrect email or password');
  redirect(safeNext(form.get('next')) ?? '/dashboard');
}

export async function signup(form: FormData) {
  const p = creds.safeParse({ email: form.get('email'), password: form.get('password') });
  if (!p.success) go('/signup', 'error', p.error.issues[0]?.message ?? 'Check your details');
  const supabase = await supabaseServer();
  const { data, error } = await supabase.auth.signUp({
    ...p.data!,
    options: { emailRedirectTo: `${await getAppUrl()}/auth/callback` },
  });
  if (error) go('/signup', 'error', error.message);
  if (data.session) redirect('/onboarding');
  go('/login', 'notice', 'Check your email to confirm your account, then sign in.');
}

export async function logout() {
  const supabase = await supabaseServer();
  await supabase.auth.signOut();
  redirect('/');
}

export async function saveProfile(form: FormData) {
  const p = profileSchema.safeParse({ fullName: form.get('full_name') });
  if (!p.success) go('/dashboard/profile', 'error', p.error.issues[0]?.message ?? 'Check your name');

  const supabase = await supabaseServer();
  const { data: { user }, error: userError } = await supabase.auth.getUser();
  if (userError || !user) {
    if (userError) console.error('saveProfile could not load user', userError.message);
    redirect('/login');
  }

  const { error } = await supabase.auth.updateUser({
    data: { full_name: p.data!.fullName },
  });
  if (error) {
    console.error('saveProfile failed', error.message);
    go('/dashboard/profile', 'error', 'Could not save profile. Please try again.');
  }

  revalidatePath('/dashboard', 'layout');
  go('/dashboard/profile', 'saved', '1');
}
