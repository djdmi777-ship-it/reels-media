# Video prompting

Generic guidance for any video model in the Hub catalog. What a specific model
accepts is in its `params` from `list_models(kind="video")`.

## Contents

- Arguments and where their limits live
- Estimating the cost
- Text-to-video prompts
- Image-to-video prompts
- End frames and audio

## Arguments and where their limits live

`generate_video` takes only these arguments: `model`, `prompt`,
`source_asset_id`, `end_asset_id`, `audio_asset_id`, `duration_seconds`,
`resolution`, `aspect_ratio`, `motion`, `idempotency_key`.

- `duration_seconds`: inside `params.duration` (`min_seconds`, `max_seconds`,
  `default_seconds`).
- `resolution`: one of `params.resolutions.options`. A model without per-second
  `billing` accepts only `params.resolutions.default` (or no value).
- `aspect_ratio`: only if the model lists aspect options.
- `motion`: only if the model offers motion presets.
- `prompt`: required unless `params.prompt_required` is `false`.
- `end_asset_id`: only with `source_asset_id` and `params.refs.end_frame`.
- `audio_asset_id`: only for models whose `params.audio` allows it.

## Estimating the cost

Read `price_basis` from `list_models`:

- `per_second_max...`: cost = `billing.rates[<resolution>].credits_per_second`
  × `duration_seconds`. `price_credits` is only the ceiling.
- `per_generation` with `credits_by_mode`: `text_to_video` without a source
  image, `image_to_video` with one. `price_credits` is the higher of the two.
- plain `per_generation`: `price_credits` per clip.

Tell the user the price for the exact settings, the balance, and how the price
changes with a longer or sharper clip. Always ask for confirmation.

## Text-to-video prompts

One paragraph in English, present tense:

1. **Subject and action**: what moves and how ("a red fox trots across fresh
   snow, then stops and looks at the camera").
2. **Camera**: shot size and movement ("slow dolly-in", "static tripod shot",
   "handheld tracking shot", "aerial orbit").
3. **Setting and light**: place, time of day, weather.
4. **Style**: live-action, anime, 3D animation, stop-motion, film look.
5. **Pacing**: "slow and calm", "one continuous shot".

Keep one clear action per clip. Several events in a few seconds usually come
out garbled. Dialogue and on-screen text are unreliable.

## Image-to-video prompts

- Pass the image as `source_asset_id`: the `asset_id` from
  `upload_file(kind="image")`, or an `assets[].id` from an earlier
  `get_generation`.
- Do not re-describe the picture; the model sees it. Describe **motion only**:
  what moves, how the camera moves, what stays still. Example: "The woman turns
  her head toward the window and smiles; her hair moves slightly in the breeze;
  slow push-in; background stays still."
- Keep the motion plausible for the image: a portrait suits subtle movement, a
  landscape suits camera moves and weather.
- If the model lets you choose `aspect_ratio`, match the source image.

## End frames and audio

- End frame: upload the second image, pass it as `end_asset_id` together with
  `source_asset_id`, and describe the transition between the two frames.
- Audio: upload with `upload_file(kind="audio")` and pass `audio_asset_id`, only
  when the model declares audio support.
