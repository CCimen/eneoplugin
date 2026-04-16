---
id: eneo.sveltekit.v1
priority: 0
paths: ["frontend/apps/web/src/routes/**"]
---

# SvelteKit route rules

Loads when editing routes. Swedish labels, typed loads, a11y, server-only secrets.

## Required per page

- `+page.server.ts` with `export const load: PageServerLoad = async ({ locals, fetch }) => { ... }`
- Every mutation via a form action in `+page.server.ts`, never via client `fetch`
- Accessible markup: `<label>` + inputs, `aria-label` on icon-only buttons, visible focus outlines
- Swedish-language labels; use `$lib/i18n` where adopted
- Server-only secrets imported via `$env/static/private` inside `.server.ts` files only

## Copy-ready skeleton

```ts
// +page.server.ts
import type { PageServerLoad, Actions } from './$types';
import { api } from '$lib/api';
import { fail, redirect } from '@sveltejs/kit';

export const load: PageServerLoad = async ({ locals, fetch }) => {
  const data = await api(fetch).<namespace>.<method>({ tenantId: locals.session.tenantId });
  return { data };
};

export const actions: Actions = {
  default: async ({ request, locals, fetch }) => {
    const form = await request.formData();
    // validate...
    try {
      await api(fetch).<namespace>.<mutation>({ tenantId: locals.session.tenantId, /* ... */ });
    } catch (err) {
      return fail(500, { reason: String(err) });
    }
    throw redirect(303, '/<next>');
  },
};
```

## Flagged on PR

- Importing `$env/static/private` in a `+page.svelte` or `+page.ts` (build will fail).
- Non-Swedish user-visible text when the file is inside an `sv`-locale route group.
- `<button onclick={fetch(...)}>` for a mutation — use a form action.
- Missing `aria-label` on an icon-only button.
