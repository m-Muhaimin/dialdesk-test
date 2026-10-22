import type { Metadata } from 'next';
import SampleWebsite from './sample-website';

export const metadata: Metadata = {
  title: 'Northstar Dental - Patient information',
  description:
    'Explore dental services, standard self-pay estimates, appointment policies, and answers to common questions.',
  robots: { index: false, follow: false },
};

export default function SampleSitePage() {
  return <SampleWebsite />;
}
