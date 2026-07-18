# v3.3 changes

- Slowed the live NMA workflow so PENDING, ANALYZING, PLANNING, confirmation, execution, and feedback are observable.
- Added paced A2C context calls and separated protection switching from service verification.
- Added intermediate `step-completed` notifications for context acquisition and analysis; the OSS refreshes the task on these pushed events without periodic polling.
- Added `A2U_DEMO_DELAY_SECONDS` to tune the live-demo pace.
- Added natural-language and structured submit-intent examples to the OpenAPI page.
