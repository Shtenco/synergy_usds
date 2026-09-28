# Security federation blocker

This repository is **not eligible for SYNERGY runtime federation** until deployer credential hygiene is completed.

## Observed repository artifact

A root-level file named `base-mainnet-deployer.key` exists in the current repository tree.

The contents were **not inspected or reproduced** during the federation audit. The filename alone is sufficient to require a fail-closed review.

## Required remediation

1. Treat the corresponding deployer credential as exposed until proven otherwise.
2. Rotate/revoke the credential at its authority source.
3. Move active secrets to an external secret manager or CI secret store.
4. Remove secret material from the current branch.
5. Purge sensitive historical blobs if the file contained a real secret.
6. Verify that no dependent deployment still relies on the old credential.
7. Add secret scanning / push protection.
8. Produce evidence of rotation and repository cleanup before federation promotion.

## Promotion rule

```text
ARCHITECTURAL_ONLY
      ↓
credential rotation verified
      ↓
secret removed from tree/history
      ↓
secret scanning enabled
      ↓
runtime capability audit
      ↓
typed contract
      ↓
ADAPTER_INTEGRATED
```

Until these conditions are met, `synergy_usds` remains `ARCHITECTURAL_ONLY`.
