# Mandatory deployer-key rotation

A file named `base-mainnet-deployer.key` is present in repository history. Its contents are intentionally not reproduced or inspected by this change.

Treat any private key ever committed to Git as compromised, even when the repository is private and even after deleting the current file, because clones, caches, CI, backups and Git history may retain it.

## Required response

1. Do not send additional funds to the old deployer address.
2. If the key controls any owner/admin/guardian role, create a new independently generated key in an HSM/MPC/offline wallet and transfer every controllable role to the new identity using the contract's documented safe ownership-transfer path.
3. Move any remaining native assets/tokens from the old EOA to the new custody arrangement after verifying destination and chain ID.
4. Revoke allowances/permissions associated with the old deployer where applicable.
5. Verify on-chain that the old key has no remaining privileged role.
6. Remove the key file from the current tree and purge it from Git history using an approved history-rewrite procedure if policy permits; coordinate this because rewriting history invalidates existing clones/SHAs.
7. Rotate any derived credentials if there is evidence they shared entropy or storage with the exposed key.
8. Record the incident and new key identifiers without storing private material in Git.

## Prevention

The accompanying `.gitignore` excludes `.private/`, `*.key`, common certificate/keystore/seed extensions and environment files.

For production use, store blockchain administration keys as non-exportable HSM/MPC keys. Repository and CI storage are not secret-management systems.
