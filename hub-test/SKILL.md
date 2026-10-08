---
name: hub-media
description: Generates images and videos, animates still images into video, and transcribes audio through the Hub MCP server (tools list_models, get_balance, upload_file, generate_image, generate_video, get_generation, transcribe), paying in Hub credits. Use this skill whenever the user asks to generate, create, draw or edit an image, picture, photo, illustration, logo, poster or cover; to make a video or clip, or animate a photo; or to transcribe a voice message, audio file, podcast, call or meeting. Also use it for Russian requests such as "сгенерируй картинку", "нарисуй", "сделай фото", "сделай видео", "оживи фото", "расшифруй аудио", "расшифруй голосовое", "сделай транскрипт", even when the user does not mention Hub by name.
---

# Hub media: images, video, transcription

The Hub MCP server (server name `hub`) sells media generation for credits from
the user's account. Every generation spends real money, so the job is to pick
the right model, say what it costs, get consent when it matters, and deliver
the result before its link expires.

## Ground rules

- **Answer in the user's language.** Talk to the user in whatever language they
  wrote in. Write prompts for media models in English unless the model's
  description says otherwise, or the user wants text in the image rendered in
  another language (keep that text verbatim, in quotes).
- **Never hardcode model ids or prices.** The catalog changes. Always call
  `list_models` (with a `kind` filter) in the current conversation before the
  first paid call of that kind, and choose from what it returns.
- **State cost and balance before any paid call.** Call `get_balance`, then tell
  the user: model, expected cost in credits, current balance.
- **Confirm before spending when it matters.** Ask for an explicit "yes" before:
  any video; any batch (more than one generation in one go); any single call
  that costs more than roughly 10% of the balance; any retry that would charge
  again. A single cheap image the user plainly asked for may run after stating
  the cost, without waiting.
- **One idempotency key per intended generation.** See "Idempotency" below. It
  is what stops a retry from charging twice.
- **Never loop on money errors.** Insufficient credits and spend-limit errors
  stop the workflow until the user acts.

## Tools

All amounts the tools return are in **credits** (the unit the user sees in the
cabinet); quote them as is.

| Tool | Arguments | Returns |
|---|---|---|
| `list_models` | `kind?` = `image` \| `video` \| `transcription` | `models[]`: `id`, `label`, `kind`, `price_credits`, `price_basis`, `credits_by_mode?`, `billing?`, `params?` |
| `get_balance` | none | `credits`, `expiring_credits`, `expiring_at`, `top_up_url` |
| `upload_file` (free) | `kind` = `image` \| `audio`; exactly one of `url` (public https, max 25 MiB) or `data_base64` (max 10 MiB decoded); `filename?` | `asset_id` (audio also `duration_ms`) |
| `generate_image` | `model`, `prompt`, `aspect_ratio?`, `quality?`, `style?`, `reference_asset_ids?`, `idempotency_key` | `request_id`, `status` |
| `generate_video` | `model`, `prompt?`, `source_asset_id?`, `end_asset_id?`, `audio_asset_id?`, `duration_seconds?`, `resolution?`, `aspect_ratio?`, `motion?`, `idempotency_key` | `request_id`, `status` |
| `get_generation` | `request_id`, `wait_seconds?` 0..20 | `status`, `credits_charged`, `assets[]` (`id`, `url`, `expires_at`), `error?` (`code`, `message`, `refunded`) |
| `transcribe` (synchronous) | exactly one of `audio_asset_id` or `url`; `model?`, `language?`, `idempotency_key` | `request_id`, `text`, `credits_charged` |

There are no other arguments. Optional fields (`aspect_ratio`, `quality`,
`style`, `motion`, `resolution`, `duration_seconds`, references) are valid only
when the chosen model's `params` declares them; the server rejects unknown or
out-of-range values.

Images upload as PNG, JPEG, WEBP or GIF; audio as MP3, WAV, AAC, M4A or OGG.

## Choosing a model and reading the price

1. Call `list_models(kind=...)`.
2. Filter by what the task needs, using `params`: reference images
   (`params.refs.max_images`), end frame (`params.refs.end_frame`), durations
   (`params.duration`), resolutions (`params.resolutions`), aspect ratios
   (`params.aspects.options`), audio input (`params.audio`), whether a prompt is
   required (`params.prompt_required`).
3. Prefer what the user asked for (quality, speed, price). With no preference,
   pick a mid-priced model that supports the needed parameters and mention a
   cheaper and a better alternative in one line.
4. A model the user names that is not in the list is not available now. Say so
   and offer the closest listed one. Never call an unlisted id.

`price_basis` says how to read `price_credits`:

- `per_generation`: `price_credits` is the price of one call. If
  `credits_by_mode` is present, the price depends on the mode:
  `text_to_video` (no `source_asset_id`) or `image_to_video` (with one);
  quote the mode you will call.
- `per_second_max...`: video priced per second. `price_credits` is the ceiling;
  actual cost = `billing.rates[resolution].credits_per_second` ×
  `duration_seconds`. Compute it for the settings you will send.
- `metered...`: transcription. `price_credits` per `billing.unit_seconds` of
  audio, rounded up to `billing.granularity_seconds`. Estimate from the audio
  length (`duration_ms` from `upload_file` helps); the charge follows the
  measured length.

## Workflow: image

1. `list_models(kind="image")` and `get_balance()`.
2. Pick a model, write the prompt (see `references/image.md`).
3. Tell the user model, cost, balance. Confirm if the rules above require it.
4. Create a new idempotency key, call `generate_image`.
5. Poll with `get_generation` (see "Polling").
6. On `succeeded`, present every `assets[].url` right away as a link (or
   download the file if you have filesystem tools and the user wants it
   saved), and report `credits_charged`.

For edits or "in the style of this picture": upload the user's image with
`upload_file(kind="image", ...)` and pass the returned `asset_id` in
`reference_asset_ids`, only if `params.refs.max_images > 0` (respect the max).

## Workflow: video

1. `list_models(kind="video")` and `get_balance()`.
2. Choose model, `duration_seconds` and `resolution` within the model's
   `params`. Default to the shortest duration and the default resolution unless
   the user asked for more; longer and sharper clips cost more.
3. Show the exact cost for these settings and the balance. **Always ask for
   confirmation.**
4. New idempotency key, call `generate_video`.
5. Poll. Video usually takes minutes; tell the user it is running.
6. Present `assets[].url` immediately.

**Animate an image** (image → video):

- Image from an earlier Hub generation: pass its `assets[].id` from
  `get_generation` as `source_asset_id`. If the server rejects that id, upload
  the fresh result URL with `upload_file(kind="image", url=...)` and use the
  returned `asset_id`.
- Image the user gave (file or link): `upload_file(kind="image", url=...)` or
  `data_base64=...`, then pass `asset_id` as `source_asset_id`.
- With `credits_by_mode`, quote the `image_to_video` price.
- The prompt should describe motion and camera, not re-describe the picture
  (see `references/video.md`).

## Workflow: transcription

1. `list_models(kind="transcription")` for model ids and metered pricing.
2. Audio source:
   - public https URL: pass `url` to `transcribe` directly; no upload needed;
   - local file or attachment: `upload_file(kind="audio", data_base64=...,
     filename=...)`, then pass `audio_asset_id`.
3. State the pricing and balance; for long recordings (over an hour, or cost
   above 10% of balance) confirm first.
4. New idempotency key, call `transcribe` with `language` if known. It is
   synchronous: long audio takes a while, the text comes back in the result.
5. Return `text` and `credits_charged`. For long transcripts, offer a summary,
   but keep the full text available. See `references/transcription.md`.

## Polling

- After `generate_*`, call `get_generation(request_id, wait_seconds=20)`.
- `status` is `queued` → `processing` → `succeeded` | `failed`. Repeat the call
  while it is `queued` or `processing`; stop at `succeeded` or `failed`.
- Every `get_generation` call counts against the key's request rate limit
  (shared with generations and uploads). Always use `wait_seconds=20` so the
  server waits for you; never poll with `wait_seconds=0` in a loop.
- Give the user a short progress note roughly every minute for long jobs.
- After about 10 minutes for images or 30 minutes for video without a terminal
  status, stop and give the user the `request_id` to check later. Do not start
  a new generation.

## Result URLs expire

`assets[].url` links expire in about 15 minutes (`expires_at`). Present or
download them immediately. If a link has expired, call `get_generation` again
for the same `request_id` to get fresh links; never regenerate to refresh one.

## Idempotency

- Generate a fresh unique `idempotency_key` (a UUID) for each generation the
  user intends, e.g. one key per image in a batch of four. Paid tools refuse to
  run without one.
- If a call times out, the connection drops, the result is unclear, or the
  server says to retry (rate limit, server error, after a top-up), retry the
  **same** call with the **same** key and the same parameters. The server
  returns the original request instead of charging again.
- Use a new key only for a genuinely new generation: changed prompt, model or
  parameters, a retry after a `failed` generation, or the user asked for
  another variant.
- For transcription, use a new key per audio file.

## Errors

Errors come back as a failed tool result whose text says what to do next.

| Error text starts with | What to do |
|---|---|
| "Not enough credits for this request" | Stop. Tell the user cost, balance and shortfall, and give the top-up link from the message (the cabinet credits page). Offer a cheaper model or settings. After the user says they topped up, retry once with the **same** idempotency key. Never retry on your own. |
| "This API key has reached its spending limit" | The key's daily spend limit is used up. Stop. Give the user the cabinet link from the message (API section) to raise or remove the limit, or wait for the reset. Do not retry until the user says so. |
| "Rate limited. Wait N seconds" | Wait N seconds, then retry the same call with the same key. At most two retries, then report. Slow down polling. |
| "Too many generations are still running" | Wait the given time; meanwhile poll running jobs with `wait_seconds=20`. Then retry with the same key. |
| "The account's upload quota is exhausted" | Stop uploading; tell the user. Prefer passing a `url` directly to `transcribe`. |
| "This model is unknown or not currently available" | Call `list_models` again, pick a listed model, tell the user about the switch and any price change before calling (new key, since parameters changed). |
| "Request rejected: ... [code]" | Validation problem (bad resolution, duration, aspect ratio, missing prompt, etc.). Fix it from the model's `params`, explain the change, retry. |
| "The API key was rejected" | Missing, wrong or revoked key. Ask the user to check `HUB_API_KEY` (or the MCP header) in their client and the key in the cabinet; restart the client. |
| "The service could not complete the request right now" | Server-side problem. Tell the user, retry later with the same key; do not loop. |
| "Could not use url: ..." | The file could not be fetched (not public, not https, too large). Ask for a direct public https link or the file itself. |

A generation that ends with `status: failed` carries `error.code`,
`error.message` and `error.refunded`. `refunded: true` means the credits came
back; offer one retry with a **new** key after asking. `refunded: false` means
the request itself was at fault (for example, rejected content); explain,
propose a rephrased prompt, and ask before spending again.

## Reporting to the user

Keep it short. Before: model, settings, cost, balance, and a question if
confirmation is needed. After: the links (or saved file paths), what was
charged, and a note that links expire in about 15 minutes.

## References

- `references/image.md` – prompting and parameters for image models.
- `references/video.md` – prompting and parameters for video and image-to-video.
- `references/transcription.md` – audio input and transcription options.
