---
name: sveltekit-load-patterns
description: Use when creating or editing any SvelteKit route under frontend/apps/web/src/routes/**. Enforces typed +page.server.ts load functions, Swedish-language labels, a11y-compliant markup, server-only secret imports, form actions for mutations, and $lib/api for all backend calls. Load this skill before writing route code so the conventions are fresh.
---

# sveltekit-load-patterns

Eneo's frontend is SvelteKit 2 with Svelte 5. Routes are written for Swedish-speaking kommun employees; a11y is non-negotiable; secrets stay on the server side.

## 1. Typed load via `+page.server.ts`

```ts
// src/routes/(app)/admin/api-keys/+page.server.ts
import type { PageServerLoad } from './$types';
import { api } from '$lib/api';


export const load: PageServerLoad = async ({ locals, fetch }) => {
  // locals.session is populated by hooks.server.ts; never read cookies here.
  const keys = await api(fetch).apiKeys.listActive({ tenantId: locals.session.tenantId });
  return { keys };
};
```

- `export const load: PageServerLoad = ...` — typed import from the generated `./$types`.
- `fetch` is the SvelteKit-aware fetch; pass it into `$lib/api` so SSR/CSR both work.
- Return data is serialized; do not return non-serializable objects (functions, class instances).

## 2. Swedish labels + a11y

```svelte
<!-- src/routes/(app)/admin/api-keys/+page.svelte -->
<script lang="ts">
  import type { PageData } from './$types';
  import { enhance } from '$app/forms';

  let { data }: { data: PageData } = $props();
</script>

<section aria-labelledby="page-heading">
  <h1 id="page-heading">API-nycklar</h1>

  <ul aria-label="Aktiva API-nycklar">
    {#each data.keys as key (key.id)}
      <li>
        <span>{key.name}</span>
        <form method="POST" action="?/revoke" use:enhance>
          <input type="hidden" name="id" value={key.id} />
          <button type="submit" aria-label="Återkalla {key.name}">
            Återkalla
          </button>
        </form>
      </li>
    {/each}
  </ul>
</section>
```

- All visible text in Swedish (or via `$lib/i18n` if the team has adopted i18n).
- Every interactive element has an accessible name: visible text, `aria-label`, or `aria-labelledby`.
- Lists use `{#each ... as ... (key)}` with a unique key expression.
- Use `use:enhance` on form actions for progressive enhancement (client-side navigation without losing SSR fallback).

## 3. Form actions for mutations (never client fetch)

```ts
// src/routes/(app)/admin/api-keys/+page.server.ts (continued)
import { fail, redirect } from '@sveltejs/kit';
import type { Actions } from './$types';


export const actions: Actions = {
  revoke: async ({ request, locals, fetch }) => {
    const form = await request.formData();
    const id = form.get('id');
    if (typeof id !== 'string') {
      return fail(400, { reason: 'missing id' });
    }

    try {
      await api(fetch).apiKeys.revoke({ id, tenantId: locals.session.tenantId });
    } catch (err) {
      return fail(500, { reason: String(err) });
    }

    throw redirect(303, '/admin/api-keys?revoked=1');
  },
};
```

- Form actions run server-side, CSRF-safe by default.
- Return `fail(status, data)` on validation / business errors; `throw redirect(303, ...)` on success.
- Don't `fetch` the backend from `+page.svelte` for mutations — always go through a form action.

## 4. Server-only secrets

```ts
// only import these in .server.ts files
import { API_BEARER_TOKEN } from '$env/static/private';
```

- Importing `$env/static/private` or `$env/dynamic/private` in a client file is a build error in SvelteKit. Don't.
- Public env vars use `$env/static/public` and must be prefixed `PUBLIC_`.

## 5. API client abstraction

All backend calls go through `$lib/api` which handles:

- Base URL resolution (respects `PUBLIC_API_BASE` + path building).
- Bearer token injection via `locals.session` (on the server) or cookie-based session (client).
- Retry-on-401 with refresh when refresh tokens are in use.

Do not hardcode `fetch('http://localhost:8000/...')`. Route through `api(fetch).<namespace>.<method>()`.

## 6. Error boundaries

Use `+error.svelte` for route-level errors:

```svelte
<!-- src/routes/(app)/admin/api-keys/+error.svelte -->
<script lang="ts">
  import { page } from '$app/stores';
</script>

<h1>Något gick fel</h1>
<p>{$page.error?.message ?? 'Okänt fel. Försök igen eller kontakta support.'}</p>
```

## 7. Accessibility checklist (tag on every page)

- [ ] `<html lang="sv">` set in `src/app.html`.
- [ ] Heading order (`h1 → h2 → h3`) not skipping levels.
- [ ] Every form field has a linked `<label>` or `aria-label`.
- [ ] Focus outline is visible (don't `outline: none` without a replacement).
- [ ] Buttons used for actions, links used for navigation — never swapped.
- [ ] Color contrast meets WCAG 2.1 AA (4.5:1 normal text, 3:1 large).
- [ ] Tab order follows visual order.

## Common mistakes

| Mistake | Fix |
|---|---|
| `fetch('/api/...')` in `+page.svelte` for mutations | Form action in `+page.server.ts` |
| Hardcoded URL `https://api.example.com/...` | `api(fetch).<namespace>.<method>()` |
| `import { SECRET } from '$env/static/private'` in `+page.svelte` | Move to `.server.ts` |
| Non-Swedish label | Swedish text or `$lib/i18n` |
| `{#each items as item}` without key | `{#each items as item (item.id)}` |
| Button with only an icon and no `aria-label` | Add `aria-label="Återkalla"` |
| Writing mutation logic in `+page.ts` (client) | Use `+page.server.ts` action |
