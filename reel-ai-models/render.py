"""Render reel.html frame by frame.
  python3 render.py probe 0.5 3 7 ...      -> out/probe/sheet.jpg
  python3 render.py chunk k n              -> out/frames/NNNNN.jpg for chunk k of n
  python3 render.py encode                 -> out/reel.mp4 (with music)
"""
import asyncio, base64, os, subprocess, sys, http.server, threading, functools
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
SONG_DROP, FILM_DROP = 130.87, 16 * 60 / 154


def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=HERE)
    h.log_message = lambda *a: None
    s = http.server.ThreadingHTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=s.serve_forever, daemon=True).start()


async def page_ctx(port):
    pw = await async_playwright().start()
    br = await pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome", args=["--force-color-profile=srgb", "--font-render-hinting=none"])
    pg = await br.new_page(viewport={"width": 1080, "height": 1920})
    await pg.goto(f"http://127.0.0.1:{port}/reel.html")
    await pg.wait_for_function("window.ready === true", timeout=60000)
    return pw, br, pg


async def grab(pg, t, path):
    data = await pg.evaluate(f"window.frameJPEG({t})")
    with open(path, "wb") as f:
        f.write(base64.b64decode(data.split(",", 1)[1]))


async def main():
    mode = sys.argv[1]
    if mode == "encode":
        return encode()
    port = 8790 + (int(sys.argv[2]) if mode == "chunk" else 9)
    serve(port)
    pw, br, pg = await page_ctx(port)
    T = await pg.evaluate("window.T")
    if mode == "probe":
        d = os.path.join(HERE, "out/probe"); os.makedirs(d, exist_ok=True)
        ts = [float(x) for x in sys.argv[2:]]
        for i, t in enumerate(ts):
            await grab(pg, t, f"{d}/p{i:02d}.jpg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{d}/p%02d.jpg", "-vf",
                        f"scale=270:-1,tile={min(len(ts), 6)}x{(len(ts) + 5) // 6}", "-frames:v", "1", f"{d}/sheet.jpg"], check=True)
    elif mode == "chunk":
        k, n = int(sys.argv[2]), int(sys.argv[3])
        N = int(round(T * FPS)); a, b = N * k // n, N * (k + 1) // n
        d = os.path.join(HERE, "out/frames"); os.makedirs(d, exist_ok=True)
        for i in range(a, b):
            await grab(pg, i / FPS, f"{d}/{i:05d}.jpg")
            if i % 60 == 0:
                print(f"chunk {k}: frame {i}/{b}", flush=True)
        print(f"chunk {k} done", flush=True)
    await br.close(); await pw.stop()


def encode():
    T = 80 * 60 / 154 + 0.5
    ss = SONG_DROP - FILM_DROP
    frames = sorted(os.listdir(os.path.join(HERE, "out/frames")))
    assert len(frames) == int(round(T * FPS)), f"frame count {len(frames)}"
    af = (f"atrim=0:{T:.3f},afade=t=in:st=0:d=0.25,afade=t=out:st={T - 1.6:.3f}:d=1.6,"
          "loudnorm=I=-14:TP=-1.3:LRA=11")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", "out/frames/%05d.jpg",
                    "-ss", f"{ss:.3f}", "-i", "src/music.mp3",
                    "-vf", "scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p",
                    "-af", af, "-c:v", "libx264", "-crf", "16", "-preset", "slow",
                    "-color_range", "tv", "-colorspace", "bt709", "-c:a", "aac", "-b:a", "256k",
                    "-t", f"{T:.3f}", "-movflags", "+faststart", "out/reel.mp4"], check=True, cwd=HERE)
    print("out/reel.mp4")


asyncio.run(main())
