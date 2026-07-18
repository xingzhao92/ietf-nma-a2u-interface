# v2 UI and A2U coverage update

- Enlarged the OSS `submit-intent` workspace and made it the primary panel.
- Exposed all draft-defined `intent-type` values: CREATE, DELETE, MODIFY,
  QUERY, REPORT, DIAGNOSE, REMEDIATE, OPTIMIZE, and ASSURE.
- Added the description of the selected intent type directly in the form.
- Exposed request-id, correlation-id, tenant-id, intent-id, submitter.type,
  and submitter.id in the OSS form.
- Added one-click GET access to the created intent, task, and confirmation
  operational-state objects.
- Replaced the single latest-notification view with a clickable notification
  history for the A2U YANG notification stream.
- Dynamically renders confirmation actions from `allowed-actions`, including
  modify-and-approve and modified-params when the confirmation permits it.
- Added inline success/error feedback and hardened correlation handling.
- Extended the smoke test to cover all intent-type enumerations and the
  modify-and-approve service workflow.
