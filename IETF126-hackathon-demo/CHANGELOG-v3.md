# v3 changes

- OpenAPI `/docs` now contains only the `ietf-nma-a2u` operational-state
  resources and the three A2U RPCs. Demo-support, compatibility, controller,
  and notification-transport endpoints are hidden.
- Added pre-populated, draft-aligned request-body examples for
  `submit-intent`, `resolve-confirmation`, and `abort-task`.
- Reworked notification delivery to follow the RFC 8639/RFC 8650 RESTCONF
  dynamic-subscription call flow:
  - `establish-subscription` returns `id` and `uri`;
  - one long-lived SSE connection activates the returned subscription URI;
  - the NMA/publisher pushes RFC 8040 JSON notification envelopes;
  - the client does not poll for notifications.
- Removed the 700 ms periodic `GET task` loop. The OSS retrieves the current
  task object after a pushed notification, after a confirmation RPC, or when
  the operator explicitly clicks the manual GET button.
- Changed the controller title to `Domain Controller`.
- Added explicit A2C controller-function records for incident context,
  service, alarm, and topology queries; incident analysis update; protection
  switching; and post-action service verification.
- Moved root-cause analysis into the NMA. The controller provides data and
  execution functions rather than making the NMA decision.
- Added a visible scrollbar to the A2U Interaction Flow panel.
- Replaced repeated notification-type chips with unique type counters plus a
  compact sequence selector.
