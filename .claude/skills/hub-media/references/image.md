# Image prompting

Generic guidance for any image model in the Hub catalog. What a specific model
accepts is in its `params` from `list_models(kind="image")`; this file never
overrides that.

## Contents

- Parameters to check in `list_models`
- Prompt structure
- Text inside the image
- Reference images and edits
- Batches and variants

## Parameters to check in `list_models`

`generate_image` takes only: `model`, `prompt`, `aspect_ratio`, `quality`,
`style`, `reference_asset_ids`, `idempotency_key`.

- `params.aspects.options`: allowed `aspect_ratio` values. If present, send one
  of them; otherwise omit the field. Map the use case: square for avatars and
  feeds, 16:9 for covers and slides, 9:16 for stories and phone wallpapers,
  4:5 or 3:4 for portrait posts.
- `params.refs.max_images`: how many reference images the model takes. `0` or
  absent means no references.
- `quality` and `style`: send only if the model lists presets for them.
- Price: `price_credits` per image (`price_basis: per_generation`).

## Prompt structure

Write one dense paragraph in English, in this order:

1. **Subject**: who or what, with concrete attributes (age, material, colour,
   count).
2. **Action and composition**: pose, framing (close-up, wide shot, top-down),
   placement in the frame.
3. **Setting**: place, time of day, weather, background.
4. **Style and medium**: photo, 3D render, watercolour, flat vector, etc. For
   photos, add lens and lighting (e.g. "85mm portrait, soft window light").
5. **Mood and palette**.
6. **Constraints**: "no text", "plain white background", "centered with empty
   space on the left for a headline".

Be specific rather than adding adjectives like "beautiful" or "high quality".
Describe what should be there, not what should not; if something must be
excluded, say so once, plainly.

Translate the user's request faithfully. Do not invent brand names, people or
extra objects the user did not ask for. Do not generate likenesses of real
private people or content the user has no rights to.

## Text inside the image

- Put the exact text in double quotes and say where it goes: `a poster with
  the headline "ЛЕТНЯЯ РАСПРОДАЖА" in bold white letters at the top`.
- Keep the user's language and spelling for the quoted text; the rest of the
  prompt stays in English.
- Short text renders more reliably. Over about six words, warn the user that
  the model may misspell it and offer to add text afterwards instead.

## Reference images and edits

- Upload each reference with `upload_file(kind="image", url=... | data_base64=...)`
  (PNG, JPEG, WEBP or GIF) and pass the returned `asset_id` values in
  `reference_asset_ids`, up to `params.refs.max_images`.
- Say in the prompt what each reference is for, in upload order: "Use the first
  image for the character's face and outfit, the second for the colour
  palette."
- For an edit, describe only the change and what must stay: "Keep the person,
  pose and framing; replace the background with a snowy mountain street at
  dusk."
- A result from an earlier Hub generation can be reused as a reference by its
  `assets[].id` from `get_generation`.

## Batches and variants

- One generation = one idempotency key. Four variants = four keys and four
  charges; show the total and ask first.
- For "try another one", ask whether to keep the prompt or change it; a new
  variant is a new key and a new charge.
