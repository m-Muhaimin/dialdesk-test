import SubmitButton from '@/components/SubmitButton';
import { saveProfile } from '@/app/actions/auth';
import { getCurrentBusiness } from '@/lib/business';

export const metadata = { title: 'Profile settings' };
export const dynamic = 'force-dynamic';

export default async function ProfileSettings({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; saved?: string }>;
}) {
  const { error, saved } = await searchParams;
  const { user } = await getCurrentBusiness();
  const fullName =
    typeof user.user_metadata?.full_name === 'string'
      ? user.user_metadata.full_name
      : '';

  return (
    <div className="max-w-2xl space-y-6">
      <section className="card space-y-4">
        <div>
          <h1 className="text-xl font-semibold">Profile settings</h1>
          <p className="mt-1 text-sm text-slate2">
            Update the name shown in your DialDesk account.
          </p>
        </div>
        {error && (
          <p role="alert" className="rounded-lg bg-alarm/10 p-3 text-sm text-alarm">
            {error}
          </p>
        )}
        {saved && (
          <p role="status" className="rounded-lg bg-live/10 p-3 text-sm text-live">
            Profile saved.
          </p>
        )}
        <form action={saveProfile} className="space-y-4">
          <div>
            <label className="label" htmlFor="full_name">Full name</label>
            <input
              id="full_name"
              name="full_name"
              type="text"
              autoComplete="name"
              defaultValue={fullName}
              maxLength={80}
              required
              className="input"
            />
          </div>
          <div>
            <label className="label" htmlFor="email">Account email</label>
            <input
              id="email"
              type="email"
              value={user.email ?? ''}
              readOnly
              className="input bg-paper text-slate2"
            />
            <p className="hint">Email changes require a separate verification flow.</p>
          </div>
          <SubmitButton>Save profile</SubmitButton>
        </form>
      </section>
    </div>
  );
}
