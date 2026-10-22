'use client';

import Script from 'next/script';
import { useEffect, useState } from 'react';

const BUSINESS_ID = '6c597d6d-c793-44d6-81eb-1cf6f5ad3e49';

type WidgetStatus = 'loading' | 'ready' | 'failed';

const services = [
  {
    title: 'Routine cleanings & checkups',
    description:
      'Comprehensive oral exams, professional cleanings, plaque and tartar removal, and polishing. We recommend a visit every six months.',
  },
  {
    title: 'Restorative care',
    description:
      'Tooth-colored composite fillings, crowns, bridges, and care for chipped or cracked teeth.',
  },
  {
    title: 'Preventative care',
    description:
      'Fluoride treatments, dental sealants, and digital X-rays to support your oral health.',
  },
  {
    title: 'Emergency dental care',
    description:
      'Same-day appointments for severe toothaches, broken teeth, lost fillings, or acute swelling and pain.',
  },
];

const faqs = [
  {
    question: 'Do you accept new patients?',
    answer: 'Yes. We are currently welcoming new patients of all ages.',
  },
  {
    question: 'Do you offer teeth whitening?',
    answer:
      'Yes. We offer professional in-office whitening and custom take-home whitening kits.',
  },
  {
    question: 'What should I do in a dental emergency after hours?',
    answer:
      'For a severe medical emergency, call 911 or visit the nearest emergency room. For urgent dental pain outside our Monday through Friday, 9:00 AM to 5:00 PM business hours, leave a message or call our emergency line. Our on-call staff will return your call promptly.',
  },
];

export default function SampleWebsite() {
  const [origin, setOrigin] = useState('https://unliteralized-blossom-tegular.ngrok-free.dev');
  const [status, setStatus] = useState<WidgetStatus>('loading');
  const [copied, setCopied] = useState(false);
  const [scriptAttempt, setScriptAttempt] = useState(0);

  useEffect(() => {
    setOrigin(window.location.origin);
  }, []);

  const snippet = `<script src="${origin}/widget.js" data-business="${BUSINESS_ID}" defer></script>`;

  async function copySnippet() {
    try {
      await navigator.clipboard.writeText(snippet);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  function openWidget() {
    const button = document.getElementById('dialdesk-widget');
    if (button instanceof HTMLButtonElement) {
      button.click();
      return;
    }
    setStatus('failed');
  }

  return (
    <main className="sample-site">
      <Script
        id="sample-dialdesk-widget"
        key={scriptAttempt}
        src="/widget.js"
        data-business={BUSINESS_ID}
        strategy="afterInteractive"
        onReady={() => {
          setStatus(
            document.getElementById('dialdesk-widget') ? 'ready' : 'failed',
          );
        }}
        onError={() => setStatus('failed')}
      />

      <header className="sample-header">
        <a href="#home" className="sample-brand" aria-label="Northstar Dental home">
          <span className="sample-brand-mark" aria-hidden="true">N</span>
          <span>Northstar <strong>Dental</strong></span>
        </a>
        <nav aria-label="Main navigation" className="sample-nav">
          <a href="#care">Our care</a>
          <a href="#fees">Fees</a>
          <a href="#visit">Plan your visit</a>
          <a href="#faqs">FAQs</a>
          <button className="sample-nav-cta" type="button" onClick={openWidget}>
            Talk to our team
          </button>
        </nav>
      </header>

      <section id="home" className="sample-hero">
        <div className="sample-hero-copy">
          <p className="sample-eyebrow">Northstar Dental</p>
          <h1>Good care starts with a conversation.</h1>
          <p className="sample-lede">
            Get clear answers, find a time that works, and feel at ease before you arrive.
          </p>
          <button className="sample-primary" type="button" onClick={openWidget}>
            Talk to our team <span aria-hidden="true">↗</span>
          </button>
        </div>
        <div className="sample-hero-image">
          <img
            src="https://images.unsplash.com/photo-1629909613654-28e377c37b09?auto=format&fit=crop&w=1400&q=85"
            alt="Bright, welcoming dental clinic reception"
            fetchPriority="high"
          />
        </div>
      </section>

      <section id="care" className="sample-care">
        <div className="sample-care-heading">
          <h2>Dental care for every stage.</h2>
          <p>
            From regular checkups to urgent concerns, our team can help you understand your options.
          </p>
        </div>
        <div className="sample-services">
          {services.map((service) => (
            <article key={service.title}>
              <h3>{service.title}</h3>
              <p>{service.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="fees" className="sample-pricing">
        <div className="sample-pricing-intro">
          <h2>Know what to expect.</h2>
          <p>
            We accept most major PPO dental insurance plans. Please verify your coverage with our
            front desk before major procedures.
          </p>
        </div>
        <div className="sample-estimates">
          <h3>Standard self-pay estimates</h3>
          <dl>
            <div>
              <dt>Routine cleaning, exam &amp; X-rays</dt>
              <dd>$150 - $250</dd>
            </div>
            <div>
              <dt>Standard composite filling</dt>
              <dd>$150 - $350 per tooth</dd>
            </div>
            <div>
              <dt>Emergency exam</dt>
              <dd>$100 - $150</dd>
            </div>
          </dl>
          <p className="sample-pricing-note">
            Emergency exam estimates exclude treatment. Maya can share general estimates, but exact
            costs depend on your clinical needs after an exam.
          </p>
        </div>
      </section>

      <section id="visit" className="sample-visit-info">
        <div className="sample-location">
          <h2>Plan your visit.</h2>
          <address>
            123 Dental Way, Suite 100
            <span>Serving local residents and nearby neighborhoods within 25 miles.</span>
          </address>
          <button className="sample-text-link" type="button" onClick={openWidget}>
            Talk to our team <span aria-hidden="true">↗</span>
          </button>
        </div>
        <div className="sample-policies">
          <article>
            <h3>Appointment length</h3>
            <p>Standard appointments are booked in 30-minute blocks.</p>
          </article>
          <article>
            <h3>Changes and cancellations</h3>
            <p>
              Please give at least 24 hours&apos; notice to cancel or reschedule. Missed
              appointments without notice may be subject to a fee.
            </p>
          </article>
          <article>
            <h3>Your first appointment</h3>
            <p>
              Please arrive 15 minutes early for registration, or complete paperwork online. Bring
              your photo ID and dental insurance card.
            </p>
          </article>
        </div>
      </section>

      <section id="faqs" className="sample-faqs">
        <div className="sample-faqs-heading">
          <h2>Common questions.</h2>
          <p>Need more help? Our team is happy to talk through your next step.</p>
          <button className="sample-primary" type="button" onClick={openWidget}>
            Talk to our team <span aria-hidden="true">↗</span>
          </button>
        </div>
        <div className="sample-faq-list">
          {faqs.map((faq) => (
            <details key={faq.question}>
              <summary>{faq.question}</summary>
              <p>{faq.answer}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="sample-visit">
        <div>
          <p className="sample-eyebrow">Widget integration</p>
          <h2>Test the complete embed.</h2>
          <p>
            The floating button below is loaded from this app using the same script you can add to
            another website.
          </p>
          <div className="sample-widget-controls">
            <div className={`sample-status sample-status-${status}`} role="status" aria-live="polite">
              <span aria-hidden="true" />
              {status === 'loading' && 'Loading widget script'}
              {status === 'ready' && 'Widget button is ready'}
              {status === 'failed' && 'Widget did not load. Check the app server and try again.'}
            </div>
            {status === 'failed' && (
              <button
                className="sample-retry"
                type="button"
                onClick={() => {
                  setStatus('loading');
                  setScriptAttempt((attempt) => attempt + 1);
                }}
              >
                Retry loading
              </button>
            )}
          </div>
        </div>
        <div className="sample-code">
          <div className="sample-code-header">
            <span>Embed code</span>
            <button type="button" onClick={copySnippet} aria-live="polite">
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
          <pre><code>{snippet}</code></pre>
          <p>Business ID: {BUSINESS_ID}</p>
        </div>
      </section>

      <footer className="sample-footer">
        <a href="#home" className="sample-brand">
          <span className="sample-brand-mark" aria-hidden="true">N</span>
          <span>Northstar <strong>Dental</strong></span>
        </a>
        <p>123 Dental Way, Suite 100</p>
      </footer>
    </main>
  );
}
