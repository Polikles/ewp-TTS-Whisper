# HTML player example

This directory is a consuming-site example, not generated transcript output. Copy an
exported `*_transcript*.html` section into `index.html`, place matching media at
`episode.mp3` (or change the audio `src`), and serve the directory over local HTTP:

```bash
python3 examples/html-player/serve.py --port 8000 --directory examples/html-player
```

Open `http://127.0.0.1:8000/`. Clicking or keyboard-activating a sentence seeks and starts
the player. Playback marks and follows the active sentence. CSS demonstrates accessible
focus, speaker colors, and light/dark presentation. Without CSS or JavaScript, the audio
controls and transcript remain in logical reading order.

Use `serve.py` for browser testing rather than Python's basic `http.server`: it implements
single HTTP byte ranges (`206 Partial Content`) needed for reliable Chromium media seeking.

The controls above the player switch between system/light/dark themes and enable or disable
automatic scrolling. To test the fallback in Chromium browsers, open DevTools, press
Ctrl+Shift+P, run `Disable JavaScript`, and reload. Run `Enable JavaScript` afterward.

Do not copy `styles.css` or `player.js` into an exported fragment. They belong to the
consuming site and are deliberately outside the renderer contract.
