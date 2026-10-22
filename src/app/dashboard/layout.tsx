import DashboardShell from './DashboardShell';
import { getCurrentBusiness } from '@/lib/business';

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { business, user } = await getCurrentBusiness();
  const userName =
    typeof user.user_metadata?.full_name === 'string' && user.user_metadata.full_name.trim()
      ? user.user_metadata.full_name.trim()
      : user.email ?? 'User';

  return (
    <DashboardShell
      businessName={business.name}
      userName={userName}
      email={user.email ?? ''}
    >
      {children}
    </DashboardShell>
  );
}
