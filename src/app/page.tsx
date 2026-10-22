import Link from 'next/link';
import { PLANS } from '@/lib/plans';

export const metadata = {
  title: 'DialDesk | A voice receptionist for your business',
  description:
    'Answer more calls, book appointments, and capture leads with a voice receptionist for your business.',
};

const benefits = [
  {
    title: 'Calls answered, even when you are busy',
    description:
      'Give callers a helpful first response while you are with a customer, on a job, or away from your desk.',
  },
  {
    title: 'Appointments that respect your hours',
    description:
      'The receptionist checks your configured availability and books appointments into the calendar.',
  },
  {
    title: 'Every conversation in one place',
    description:
      'Review calls, transcripts, appointments, and captured leads from your dashboard.',
  },
];

const proFeatures = [
  `${PLANS.pro.callsPerMonth} calls each month`,
  'Everything in Free',
  'Appointment booking and lead capture',
  'Call history and transcripts in your dashboard',
  'Manage your plan from billing settings',
];

const freeFeatures = [
  `${PLANS.free.callsPerMonth} calls each month`,
  'Website voice receptionist widget',
  'Business hours and service configuration',
  'Dashboard for calls, appointments, and leads',
];

export default function Home() {
  return (
    <main className="overflow-hidden">
      <header className="mx-auto flex min-h-[72px] max-w-7xl items-center justify-between gap-4 px-5 md:px-8">
        <Link href="/" className="whitespace-nowrap text-lg font-bold tracking-tight">
          Dial<span className="text-lamp">Desk</span>
        </Link>
        <nav className="flex items-center gap-2 sm:gap-5" aria-label="Main navigation">
          <a href="#how-it-works" className="hidden text-sm font-medium text-slate2 hover:text-ink sm:inline">
            How it works
          </a>
          <a href="#pricing" className="hidden text-sm font-medium text-slate2 hover:text-ink sm:inline">
            Pricing
          </a>
          <Link href="/login" className="rounded-lg px-3 py-2 text-sm font-semibold text-ink hover:bg-white">
            Sign in
          </Link>
          <Link href="/signup" className="btn">
            Start free
          </Link>
        </nav>
      </header>

      <section className="mx-auto grid max-w-7xl items-center gap-10 px-5 pb-16 pt-10 md:grid-cols-[1fr_0.9fr] md:gap-16 md:px-8 md:pb-24 md:pt-14">
        <div className="max-w-2xl">
          <p className="mb-5 text-xs font-semibold uppercase tracking-widest text-slate2">
            A voice receptionist for local business
          </p>
          <h1 className="text-4xl font-semibold leading-[1.08] tracking-tight md:text-6xl">
            Never miss the call that books the job.
          </h1>
          <p className="mt-5 max-w-xl text-base leading-7 text-slate2 md:text-lg">
            DialDesk answers callers, checks availability, and captures every lead while you focus on
            the work in front of you.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link href="/signup" className="btn px-5 py-3">
              Create your receptionist
            </Link>
            <a href="#how-it-works" className="btn-ghost px-5 py-3">
              See how it works
            </a>
          </div>
          <p className="mt-4 text-sm text-slate2">
            Start with {PLANS.free.callsPerMonth} calls per month on the Free plan.
          </p>
        </div>
        <div className="relative">
          <img
            src="https://images.unsplash.com/photo-1551836022-d5d88e9218df?auto=format&fit=crop&w=1200&q=85"
            alt="Small business team helping a customer at work"
            fetchPriority="high"
            className="h-[300px] w-full rounded-xl object-cover md:h-[440px]"
          />
          <div className="mt-3 flex items-center justify-between gap-4 text-sm text-slate2">
            <span>More time for the work only you can do.</span>
            <span className="shrink-0 font-medium text-ink">DialDesk</span>
          </div>
        </div>
      </section>

      <section className="border-y border-mist bg-white px-5 py-16 md:px-8 md:py-20">
        <div className="mx-auto grid max-w-7xl gap-10 md:grid-cols-[0.8fr_1.2fr] md:gap-16">
          <div>
            <h2 className="max-w-md text-3xl font-semibold tracking-tight md:text-4xl">
              Be there for every caller.
            </h2>
            <p className="mt-4 max-w-md text-base leading-7 text-slate2">
              Missed calls can mean missed work. DialDesk gives callers a clear next step and gives
              your team the details to follow up.
            </p>
          </div>
          <div className="grid gap-7 sm:grid-cols-2">
            {benefits.map((benefit, index) => (
              <article
                key={benefit.title}
                className={index === 0 ? 'sm:col-span-2 sm:max-w-xl' : ''}
              >
                <span className="text-sm font-bold text-lamp">0{index + 1}</span>
                <h3 className="mt-2 text-lg font-semibold">{benefit.title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate2">{benefit.description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="how-it-works" className="mx-auto max-w-7xl px-5 py-16 md:px-8 md:py-24">
        <div className="max-w-xl">
          <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">
            Set up once. Get back to work.
          </h2>
          <p className="mt-4 text-base leading-7 text-slate2">
            Add your business details, connect the widget, and let DialDesk handle the first
            conversation.
          </p>
        </div>
        <div className="mt-10 grid gap-8 border-t border-mist pt-7 md:grid-cols-[1.2fr_0.9fr_0.9fr] md:gap-12">
          <article>
            <span className="text-sm font-bold text-lamp">01</span>
            <h3 className="mt-3 max-w-sm text-2xl font-semibold tracking-tight">
              Tell DialDesk how your business works.
            </h3>
            <p className="mt-3 max-w-md text-sm leading-6 text-slate2">
              Set your hours, services, appointment length, and the details callers need to know.
            </p>
          </article>
          <article className="border-t border-mist pt-5 md:border-t-0 md:pt-0">
            <span className="text-sm font-bold text-lamp">02</span>
            <h3 className="mt-2 text-lg font-semibold">Add the website widget</h3>
            <p className="mt-2 text-sm leading-6 text-slate2">
              Place one script on your site to give visitors a way to talk with your receptionist.
            </p>
          </article>
          <article className="border-t border-mist pt-5 md:border-t-0 md:pt-0">
            <span className="text-sm font-bold text-lamp">03</span>
            <h3 className="mt-2 text-lg font-semibold">Follow up from your dashboard</h3>
            <p className="mt-2 text-sm leading-6 text-slate2">
              See booked appointments, new leads, and call transcripts together.
            </p>
          </article>
        </div>
      </section>

      <section id="pricing" className="bg-white px-5 py-16 md:px-8 md:py-24">
        <div className="mx-auto max-w-7xl">
          <div className="max-w-xl">
            <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">
              Plans that scale with your calls.
            </h2>
            <p className="mt-4 text-base leading-7 text-slate2">
              Start free, then move to Pro when your business needs more monthly call capacity.
            </p>
          </div>
          <div className="mt-10 grid gap-5 md:grid-cols-2">
            <article className="flex flex-col rounded-xl border border-mist bg-paper p-6 md:p-8">
              <div>
                <p className="text-sm font-semibold text-slate2">Free</p>
                <p className="mt-3 text-4xl font-semibold tracking-tight">
                  $0 <span className="text-base font-medium text-slate2">/ month</span>
                </p>
                <p className="mt-3 text-sm leading-6 text-slate2">
                  Try the receptionist with the essential tools to get started.
                </p>
                <ul className="mt-6 space-y-3 text-sm">
                  {freeFeatures.map((feature) => (
                    <li key={feature} className="flex gap-3">
                      <span className="font-bold text-live" aria-hidden="true">✓</span>
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <Link href="/signup" className="btn-ghost mt-8 w-full">
                Start free
              </Link>
            </article>

            <article className="flex flex-col rounded-xl border-2 border-ink bg-ink p-6 text-white md:p-8">
              <div>
                <p className="text-sm font-semibold text-white/70">Pro</p>
                <p className="mt-3 text-3xl font-semibold tracking-tight">
                  {PLANS.pro.callsPerMonth} calls
                  <span className="text-base font-medium text-white/70"> / month</span>
                </p>
                <p className="mt-3 text-sm leading-6 text-white/75">
                  More capacity for a busy front desk. Your subscription price is shown before you
                  confirm at checkout.
                </p>
                <ul className="mt-6 space-y-3 text-sm">
                  {proFeatures.map((feature) => (
                    <li key={feature} className="flex gap-3">
                      <span className="font-bold text-lamp" aria-hidden="true">✓</span>
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <Link
                href="/signup"
                className="mt-8 inline-flex min-h-11 w-full items-center justify-center rounded-lg bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:bg-white/90"
              >
                Create an account
              </Link>
            </article>
          </div>
        </div>
      </section>

      <section className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-6 px-5 py-16 md:flex-row md:items-center md:px-8 md:py-20">
        <div className="max-w-2xl">
          <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">
            Give every caller a helpful first response.
          </h2>
          <p className="mt-3 text-base leading-7 text-slate2">
            Set up your receptionist and see how DialDesk fits your business.
          </p>
        </div>
        <Link href="/signup" className="btn shrink-0 px-5 py-3">
          Start free
        </Link>
      </section>

      <footer className="border-t border-mist bg-white px-5 py-6 md:px-8">
        <div className="mx-auto flex max-w-7xl flex-col justify-between gap-3 text-sm text-slate2 sm:flex-row sm:items-center">
          <Link href="/" className="w-fit font-bold tracking-tight text-ink">
            Dial<span className="text-lamp">Desk</span>
          </Link>
          <p>Voice reception and call management for local businesses.</p>
          <Link href="/login" className="w-fit font-medium text-ink hover:underline">
            Sign in
          </Link>
        </div>
      </footer>
    </main>
  );
}
