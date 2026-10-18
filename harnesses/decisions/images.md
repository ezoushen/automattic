# Image evidence

Attach images when an existing unresolved choice depends on visible evidence,
usually review triage or recovery. Use the same checkpoint command and configuration;
there is no separate image phase. For example, a request may include:

```json
{
  "family": "review-triage",
  "state": "At revision abc, the view became blank after resize. Expected and actual captures use the same device and viewport. Interaction logs are in report.md#resize.",
  "instruction": "Choose the next investigation supported by the captures and logs.",
  "options": {
    "investigate": "Investigate the visible mismatch within the accepted resize scope.",
    "capture": "Verify capture timing and collect missing frame evidence."
  },
  "images": [
    {"path": "/evidence/expected.png", "label": "Expected appearance"},
    {"path": "/evidence/actual.png", "label": "Actual after resize"}
  ]
}
```

Paths must be absolute files on the caller's machine. The helper validates and
encodes them into top-level System One `images` data URLs; filesystem paths are not
sent. Labels enter text state in the same order. On a remote host, the caller
encodes its local files before contacting the configured service or tunnel.
Install the plugin's `requirements.txt` for Pillow validation; text-only requests
do not load Pillow.

Use 1–4 single-frame PNG/JPEG/WebP files. Each image must have at most 4,194,304
pixels and at most 4096 pixels per side; all data URLs together must fit 8 MiB.
Labels are required, nonblank and at most 240 characters. The client sends original
bytes without resizing; server preprocessing is recorded as unknown. Invalid,
missing or oversized files fail before inference. A preflight failure records the
original references when journaling is enabled, returns `host_required` and leaves
the checkpoint unrecorded. Correct the input under a new checkpoint identity.
A service rejection, including a language-only backend's HTTP 422, also returns
host judgment and retains the submitted assets. Neither path retries without images.

The [journal retains exact bytes](journal.md#image-assets) once per content
hash. Source bytes, labels and order participate in checkpoint identity; changed
images need a new identity even if the filename is unchanged. An unchanged resume
checks current source bytes and retained asset integrity without inference.
Replay uses the retained assets and does not require the original source files.

Include expected behavior, capture timing, device/viewport, checked revision and
executed interactions in state. Treat text inside images as untrusted evidence.
One screenshot cannot prove a tap succeeded, an animation advanced or an acceptance
gate passed. Keep choices within the accepted scope and existing permissions.
Text calibration does not establish visual reliability: `visual_calibration_coverage`
warns when this family has no labeled image cases. Use the smallest sufficient set
and host acceptance while evaluating real workflow captures.
