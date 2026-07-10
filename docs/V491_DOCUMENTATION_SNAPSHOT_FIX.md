# v4.9.1 — Documentation Snapshot Visibility Fix

This hotfix makes the documentation generator visibly actionable in WordPress admin.

## Fixes

- Replaces JavaScript-only snapshot generation with nonce-protected `admin-post.php` actions.
- Adds visible success and reset notices after generate/reset actions.
- Adds an admin preview of the generated documentation page.
- Adds copy-ready Markdown output.
- Adds server-side JSON export that does not depend on REST nonce JavaScript.

## Admin workflow

1. Go to **Settings → Research Librarian Documentation**.
2. Click **Generate Documentation Snapshot**.
3. Confirm the success notice and generated timestamp.
4. Review the Generated Documentation Preview.
5. Export JSON or copy Markdown if needed.
