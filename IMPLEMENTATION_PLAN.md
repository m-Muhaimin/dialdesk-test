# DialDesk --- Implementation Plan

**File:** `IMPLEMENTATION_PLAN.md`\
**Purpose:** Build a complete DialDesk voice SaaS by extending the
existing Next.js application and Python voice service with shared
session management, inbound Twilio calling, multi-tenant configuration,
persistent call records, billing, knowledge management, and production
operations.

## 1. Implementation Guide

Use this plan as the implementation guide for the target architecture
and delivery sequence. The goal is to preserve the existing working
voice experience while adding product and telephony capabilities around
a shared voice runtime.

The central design decision is to separate: 1. The application backend
and SaaS features. 2. Browser and telephony transport adapters. 3. The
shared voice runtime and conversation logic. 4. Persistent data,
asynchronous jobs, usage accounting, and analytics.

Phone and browser sessions use different media transports, but should
share the same agent configuration, business tools, conversation
behavior, tenant authorization, and call lifecycle.

Do not create separate, independently maintained AI agents for browser
and phone unless a concrete product requirement demands it.

## 2. Target Architecture

``` text
                    DialDesk Next.js application
        Dashboard · Organizations · Agents · Settings
             Billing · Call history · Knowledge base
                              |
                    Authenticated application API
                              |
             +----------------+----------------+
             |                                 |
      Browser voice adapter             Telephony adapter
      WebRTC signaling                   Twilio webhooks
      Browser session                    Media Streams
             |                                 |
             +----------------+----------------+
                              |
                    Shared voice runtime
           Pipecat · audio frames · VAD · endpointing
             STT · LLM · TTS · interruption handling
                    shared business tools
                              |
                  Durable data and job layer
        Database · lifecycle events · usage · analytics
```

### Service responsibilities

**Next.js application** - Owns authentication, organizations,
membership, agent configuration, business rules, billing, and
persistence. - Exposes authenticated APIs for session configuration and
tool execution. - Resolves the authorized organization and agent before
a voice session starts. - Remains the source of truth for call status,
tenant ownership, and usage.

**Browser adapter** - Owns browser-specific session setup, WebRTC
signaling, and browser media connection handling. - Uses the shared
voice runtime and common session contract. - Keeps browser transport
details out of business logic.

**Telephony adapter** - Owns Twilio webhook handling, request-signature
validation, TwiML responses, and Media Streams connection setup. -
Resolves the called number to an authorized organization and agent. -
Uses the same shared voice runtime and business tools as browser calls.

**Shared voice runtime** - Owns audio processing, VAD, endpointing,
STT/LLM/TTS orchestration, tool-call coordination, interruptions,
cancellation, and session cleanup. - Uses a Pipecat-compatible transport
for phone media where supported by the installed version. - Keeps
transport-specific code separate from conversation and business logic.

**Data and jobs** - Persist calls, transcripts, lifecycle events, agent
configuration, and usage. - Run non-real-time jobs such as document
ingestion and analytics. - Support idempotent usage accounting and
recoverable finalization.

## 3. Delivery Phases

Implement the system incrementally. Each phase must leave the product in
a testable state.

### Phase 1 --- Stabilize the existing voice runtime

**Tasks** - \[ \] Standardize call and session lifecycle transitions. -
\[ \] Add structured timing, error reporting, and resource cleanup. - \[
\] Test STT, LLM, TTS, and function calls independently. - \[ \] Ensure
interruption and cancellation do not leave stale generation or playback
running. - \[ \] Add tests for provider errors, disconnects, and session
teardown. - \[ \] Record baseline end-to-end latency before performance
changes. - \[ \] Verify that the current browser voice flow continues to
work.

**Acceptance criteria** - The current browser conversation flow works
end to end. - Provider failures and disconnects lead to controlled
cleanup. - Per-stage timing can be used to identify the main latency
bottleneck.

### Phase 2 --- Implement multi-tenant application data

**Tasks** - \[ \] Add organization-scoped agent configuration. - \[ \]
Persist prompts, language, voice settings, enabled tools, and
knowledge-source configuration. - \[ \] Persist calls, transcripts,
outcomes, and final status. - \[ \] Enforce tenant isolation in
application APIs and database access. - \[ \] Validate agent
configuration before starting a session. - \[ \] Use foreign keys,
indexes, unique constraints, and row-level security where supported. -
\[ \] Keep provider credentials and internal service secrets
server-side.

**Suggested data model**

  ------------------------------------------------------------------------
  Table                    Key fields              Purpose
  ------------------------ ----------------------- -----------------------
  `organizations`          `id`, `name`, `plan_id` Tenant and billing
                                                   owner

  `organization_members`   `organization_id`,      Membership and
                           `user_id`, `role`       permissions

  `agents`                 `id`,                   Agent configuration
                           `organization_id`,      
                           `name`,                 
                           `system_prompt`,        
                           `settings`              

  `phone_numbers`          `id`,                   Phone-number assignment
                           `organization_id`,      
                           `agent_id`, `provider`, 
                           `provider_number_id`    

  `calls`                  `id`,                   Canonical call record
                           `organization_id`,      
                           `agent_id`, `channel`,  
                           `status`, `started_at`, 
                           `ended_at`              

  `call_transcripts`       `call_id`, `role`,      Conversation history
                           `text`, `sequence`      

  `knowledge_sources`      `id`,                   Knowledge source
                           `organization_id`,      tracking
                           `type`, `status`        

  `usage_events`           `organization_id`,      Auditable metering
                           `call_id`,              inputs
                           `event_type`,           
                           `quantity`              
  ------------------------------------------------------------------------

**Acceptance criteria** - Two organizations cannot read or mutate each
other's records. - Agent settings are loaded and authorized on the
server. - Call records and transcripts survive service restarts.

### Phase 3 --- Define the application/runtime contract

The application must authenticate a user or validate the incoming
telephony webhook, resolve the organization and agent, create or resolve
a call record, and issue a short-lived signed session token or
equivalent authenticated internal session.

Example internal session configuration:

``` json
{
  "call_id": "call_123",
  "organization_id": "org_456",
  "agent_id": "agent_789",
  "channel": "phone",
  "language": "en",
  "voice": "default",
  "enabled_tools": [
    "check_availability",
    "book_appointment",
    "capture_lead"
  ]
}
```

This is an illustrative internal contract, not a credential or a payload
to trust from an unauthenticated client. IDs, enabled tools, prompt, and
permissions must be verified from server-side records.

**Tasks** - \[ \] Define and validate the session configuration
schema. - \[ \] Authenticate internal service-to-service requests. - \[
\] Version the runtime protocol. - \[ \] Standardize lifecycle events
shared by browser and phone sessions. - \[ \] Include call ID, event
timestamp, channel, turn ID where applicable, and correlation ID. - \[
\] Avoid putting secrets or unnecessary sensitive content in event
payloads. - \[ \] Persist important events, especially final call status
and billable usage, durably.

**Standard lifecycle events**

  Event                          Purpose
  ------------------------------ --------------------------------------
  `call.started`                 Record session start
  `transcript.partial`           Optional interim recognition result
  `transcript.final`             Persist a finalized utterance
  `tool.started`                 Track a business action
  `tool.completed`               Record the action result
  `assistant.started_speaking`   Measure time to first audio
  `call.ended`                   Record final status and duration
  `call.failed`                  Capture recoverable or fatal failure

### Phase 4 --- Add inbound Twilio calling

Implement telephony as a new transport adapter; do not replace the
browser transport.

**Inbound call flow** 1. A caller dials a provisioned Twilio number. 2.
Twilio sends an HTTP webhook to the Next.js application. 3. The
application validates Twilio's request signature, resolves the number to
the authorized organization and agent, and creates a call record. 4. The
webhook returns TwiML directing Twilio to a secure WebSocket Media
Streams endpoint. 5. The telephony adapter authenticates the session and
connects it to the shared voice runtime. 6. Caller audio passes through
speech recognition, response generation, tools if needed, and speech
synthesis. 7. The runtime returns audio in the format expected by
Twilio. 8. Lifecycle events and transcripts are persisted, and the
application finalizes the call when the stream ends.

**Tasks** - \[ \] Add the inbound Twilio voice webhook. - \[ \] Validate
Twilio request signatures. - \[ \] Resolve inbound phone numbers to the
correct tenant and agent. - \[ \] Connect Twilio Media Streams to a
supported Pipecat-compatible telephony transport/serializer after
verifying compatibility with the installed Pipecat version. - \[ \]
Share session configuration, business tools, and lifecycle logic across
browser and phone pipelines. - \[ \] Keep transport-specific audio
framing and connection handling separate. - \[ \] Test audio conversion,
playback timing, disconnects, and interruptions. - \[ \] Add explicit
session ownership/routing for horizontally scaled workers.

**Audio requirements** - Telephony media commonly uses 8 kHz μ-law.
Decode and resample correctly for processing, then encode output into
the format Twilio expects. - Verify sample rate, channel count, frame
duration, byte order, and payload format at each boundary. - Stop
playback and invalidate obsolete responses when a caller interrupts. -
Do not assume that a transport implementation working in a browser will
automatically work for Twilio.

**Acceptance criteria** - A real inbound call connects and receives the
configured greeting. - Caller audio is processed and the assistant
response is audible. - Call records, transcripts, and final status are
persisted. - Disconnects, provider failures, and interruption do not
leave sessions stuck. - Existing browser conversations continue to work.

### Phase 5 --- Build SaaS features around the canonical data model

Implement product capabilities in this order.

**Agent management** - \[ \] Allow each organization to configure agent
name, greeting, instructions, language, voice, business hours, enabled
tools, and escalation rules. - \[ \] Validate all configuration before
starting a call. - \[ \] Keep prompts and tool permissions
server-controlled.

**Call history and analytics** - \[ \] Display call status, duration,
transcript, lead information, booking outcome, failure reason, and
usage. - \[ \] Support filtering by agent, date, and channel. - \[ \]
Derive dashboard views from canonical persisted records.

**Knowledge base** - \[ \] Implement document ingestion, chunking,
indexing, and retrieval. - \[ \] Scope every source and retrieval query
to the authorized organization. - \[ \] Track source status and
ingestion errors. - \[ \] Provide traceability for retrieved
information.

**Billing and usage** - \[ \] Track call duration and other billable
events in a durable usage ledger. - \[ \] Make usage processing
idempotent. - \[ \] Reconcile provider events with the internal ledger
before charging customers. - \[ \] Test payment checkout and billing
webhooks separately from voice tests.

**Privacy** - \[ \] Define transcript and recording retention periods. -
\[ \] Implement access control, consent handling, and deletion workflows
appropriate to the product's markets. - \[ \] Do not retain raw audio
indefinitely by default.

### Phase 6 --- Production hardening and scale

**Tasks** - \[ \] Add rate limits, concurrency caps, bounded queues,
timeouts, and retry policies. - \[ \] Add graceful shutdown and reliable
cleanup of active sessions. - \[ \] Make call finalization idempotent in
persistent storage; do not rely only on in-memory guards. - \[ \] Retry
transient finalization failures or place them in a durable retry
mechanism. - \[ \] Use a queue or worker infrastructure for
non-real-time jobs such as document ingestion and analytics. - \[ \] Add
structured logs and metrics for each call and turn. - \[ \] Load-test
concurrent calls and document capacity limits. - \[ \] Test failure and
recovery for STT, LLM, TTS, tools, database access, and network
disconnects.

**Required metrics** - Time to first transcript. - End-of-turn delay. -
LLM time to first token. - TTS time to first audio. - Time to first
audible response. - Total response latency. - Call completion and
failure rates. - Provider/tool failure counts. - Disconnects, audio
gaps, dropped frames, and interruption outcomes.

## 4. Suggested Repository Structure

This is a proposed target layout. Keep existing conventions and move
code incrementally.

``` text
dialdesk/
├── src/
│   ├── app/
│   │   └── api/
│   │       ├── webhooks/
│   │       │   └── twilio/
│   │       │       └── voice/route.ts
│   │       ├── organizations/
│   │       ├── agents/
│   │       ├── calls/
│   │       ├── phone-numbers/
│   │       └── billing/
│   └── lib/
│       ├── auth/
│       ├── organizations/
│       ├── agents/
│       ├── calls/
│       ├── voice/
│       │   ├── session.ts
│       │   ├── config.ts
│       │   └── events.ts
│       └── billing/
├── voice-pipeline/
│   ├── web_voice.py
│   ├── phone_voice.py
│   ├── session.py
│   ├── config.py
│   ├── events.py
│   ├── tools/
│   └── tests/
├── supabase/
│   └── migrations/
└── docs/
    ├── architecture.md
    └── telephony.md
```

The layout is illustrative. Confirm existing paths before creating or
moving files.

## 5. End-to-End Acceptance Checklist

### Voice runtime

-   [ ] Browser conversations continue to work after refactoring.
-   [ ] Tool calls execute with the correct organization and
    permissions.
-   [ ] Interrupted speech cancels playback and invalidates stale model
    output.
-   [ ] STT, LLM, and TTS failures produce controlled recovery behavior.

### Telephony

-   [ ] A real inbound Twilio call connects and receives a greeting.
-   [ ] Caller audio is transcribed and the assistant response is
    audible.
-   [ ] Audio format and timing are correct in both directions.
-   [ ] Disconnects and timeouts close sessions cleanly.
-   [ ] Concurrent calls do not share state or audio.

### SaaS

-   [ ] Organizations cannot access each other's calls, transcripts,
    agents, or knowledge.
-   [ ] Agents and phone numbers can be configured through the
    dashboard.
-   [ ] Call transcripts and final status survive a service restart.
-   [ ] Usage accounting is durable and idempotent.

### Operations

-   [ ] Connection, rate, duration, and concurrency limits are enforced.
-   [ ] Per-stage latency and failures are observable.
-   [ ] Retention and deletion policies are documented and tested.
-   [ ] Load and provider-failure tests pass against defined service
    targets.

## 6. Recommended Execution Order

1.  Stabilize the existing voice runtime and add baseline tests.
2.  Establish the multi-tenant agent and call data model.
3.  Define the shared session configuration and lifecycle events.
4.  Add the inbound Twilio adapter using the shared voice runtime.
5.  Verify browser and phone calls end to end.
6.  Add agent management, call history, and analytics.
7.  Add knowledge-base ingestion and retrieval.
8.  Add durable usage metering and billing.
9.  Harden scaling, recovery, privacy, and operational controls.

## 7. Release Gate

Do not consider the system production-ready until: - \[ \] Build, lint,
type checks, and automated tests pass. - \[ \] Browser and real Twilio
calls pass end-to-end tests. - \[ \] Interruption and cancellation work
correctly. - \[ \] Provider and tool failures have bounded recovery
behavior. - \[ \] Tenant isolation and authorization tests pass. - \[ \]
Call finalization and usage accounting are durable and idempotent. - \[
\] Latency and concurrency are measured against explicit targets. - \[
\] Secrets management, observability, retention, and incident procedures
are documented.

## Guiding Principle

Keep transport, voice orchestration, and business logic separate. Build
phone and browser experiences on the same agent configuration, business
tools, and call lifecycle. Prioritize reliable calls, tenant isolation,
and operational visibility before expanding the feature set.
