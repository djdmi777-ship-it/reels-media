# Transcription

Generic guidance for any transcription model in the Hub catalog. Model ids and
pricing come from `list_models(kind="transcription")`.

`transcribe` takes only: exactly one of `audio_asset_id` or `url`, plus
`model?`, `language?` and `idempotency_key`. There are no other options.

## Contents

- Getting the audio in
- Arguments
- Cost
- Presenting the transcript

## Getting the audio in

- **Public https URL** (a direct link to the file): pass it as `url` to
  `transcribe`. The server downloads it (max 25 MiB) and transcribes it
  directly; no `upload_file` step is needed. Links to web pages with an
  embedded player usually do not work; ask for a direct file link or the file.
- **Local file or chat attachment**: base64-encode it and call
  `upload_file(kind="audio", data_base64=..., filename=...)` (max 10 MiB
  decoded). Keep the original filename with its extension. Pass the returned
  `asset_id` as `audio_asset_id`. The upload also returns `duration_ms`, which
  lets you estimate the price.
- Accepted formats: MP3, WAV, AAC, M4A, OGG.
- **Video file or large recording**: if you have a shell with ffmpeg, extract
  or compress the audio (mono, lower bitrate) to fit the limits. Otherwise ask
  the user for a smaller file or a public link.

## Arguments

- `model`: an id from `list_models(kind="transcription")`. It is
  optional, but pass it explicitly so the price you quoted is the price of the
  model that runs.
- `language`: the speech language code (e.g. `ru`, `en`) when known; it helps
  accuracy on short or noisy clips.

## Cost

Transcription is metered: `price_credits` per `billing.unit_seconds` of audio,
rounded up to `billing.granularity_seconds`. Estimate from the duration if you
know it; otherwise state the rate and that the charge follows the measured
length. Confirm for long recordings. The result reports `credits_charged`.

## Presenting the transcript

- Return the full `text`. For long transcripts, save it to a file if you can
  and give the path, then offer a summary, action items or a translation as a
  separate step (these are not Hub calls and cost no credits).
- The transcript stays in the recording's language; talk to the user in theirs.
- Use a new `idempotency_key` for each file. Reusing a key with a different
  file of the same name and size can return the earlier result.
