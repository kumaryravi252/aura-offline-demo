# AURA — Adaptive Unstructured Road Autonomy

An offline, presentation-ready research demo for unmarked-road reasoning: perception inputs → object tracking → behavior heuristics → uncertainty-aware prediction → risk grid → driving decisions.

**Start here:** the default mode is a working, deterministic simulator with synthetic detections. It runs with Python alone. Optional camera/video inference requires separate local model weights and packages. This is not a trained end-to-end autonomous driving system, nor suitable for controlling a real vehicle.

## Run in 30 seconds

1. Install Python 3.10 or newer if needed (the project was tested on Python 3.12).
2. Extract the ZIP and open a terminal in the `aura-demo` folder.
3. Run:

```bash
python server.py
```

On Windows, `py -3 server.py` or double-click `start.bat`. On Linux/macOS, `python3 server.py` or `./start.sh`.

4. Open **http://127.0.0.1:8000** in Chrome, Edge, or Firefox.
5. Disconnect Wi-Fi to demonstrate local operation. Keep the Python terminal running.

No npm installation, pip packages, API keys, CDNs, map downloads, or internet are needed for simulation. Node is optional and used only for the development preview script. Do not open `index.html` directly: the frontend needs its local Python API.

## What is implemented

| Presentation feature | Implementation | Scope |
|---|---|---|
| Camera input | Optional local OpenCV video/camera capture | Single camera; no bundled footage or model |
| Object detection | Synthetic detections by default; optional local YOLO inference | Human, animal, bike, bus, general vehicle; auto/thela need custom weights for vision |
| Road scene understanding | Known unmarked-road corridor in simulator | Manual image-space corridor in vision; no learned road segmentation |
| Object tracking | Class-gated nearest-neighbor association, alpha-beta motion filter | IDs are inferred; not copied from simulated objects |
| Behavior understanding | Crossing, steady, decelerating, stationary, occluded | Explainable rules, not a learned behavior classifier |
| Trajectory prediction | Constant-velocity extrapolation with class-dependent uncertainty | Configurable 1–5-second horizon |
| Risk / safe space | 16 × 30 risk grid and five candidate paths | Heuristic scores, not calibrated accident probabilities |
| Driving decision | CONTINUE / SLOW / STOP, with caution-release hysteresis | Explainable reason displayed on every update |
| Vehicle response | Simulated speed and brake response; recommended lateral target | No real actuator connection; recommended steering is not executed |
| Additional algorithm | Occlusion-aware track memory | Two-second coasting and growing uncertainty |
| Offline architecture | Local HTTP server, local assets, local computation | Initial optional vision setup requires downloads beforehand |

## Demo sequence for judges

Open **Presenter guide** inside the app, or read [docs/PRESENTATION.md](docs/PRESENTATION.md).

1. **Unstructured street:** six classes, no lane markings, evolving paths and risk.
2. **Human vs animal:** same forward distance and zero motion; animal envelope has a larger radius and faster uncertainty growth. Raise the horizon, then use Step if paused.
3. **Hidden pedestrian:** from 3.0 to 4.5 seconds the pedestrian is unobserved. Pause during this window and toggle occlusion memory. The track remains in the table; memory controls whether it contributes to planning risk.
4. **Pedestrian crossing / sudden bus stop:** explain changes in risk and speed targets.
5. **Clear road:** CONTINUE follows the 0.8-second caution release.
6. **Export run:** download the current state and recent simulated history as JSON.

Changing scenarios resets the simulator. Pausing preserves the current output. Step advances 0.1 seconds. Changing memory while paused advances one step to recompute; other slider changes apply on the next step. The server has one shared demonstration session: use one active browser tab.

## Optional real camera / road-video mode

This adapter follows the official [Ultralytics prediction API](https://docs.ultralytics.com/modes/predict/) and [OpenCV video capture](https://docs.opencv.org/3.4.18/dd/d43/tutorial_py_video_display.html).

While you still have internet access:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux instead:
# source .venv/bin/activate
python -m pip install -r requirements-vision.txt
```

Download trusted detection weights, for example `yolo11n.pt`, from the official Ultralytics model release linked by their documentation. Put them at `models/yolo11n.pt`. The server requires an existing file and never intentionally downloads a model. Only load trusted weights. Optional dependency ranges are not a reproducibility lock; after verifying your machine, record versions with `python -m pip freeze > requirements-vision-lock.txt`.

Then run offline:

```bash
# A camera connected to the same laptop as the Python server:
python server.py --model models/yolo11n.pt --source 0
# Or a local recording; quote paths containing spaces:
python server.py --model models/yolo11n.pt --source "road.mp4"
```

The dashboard automatically switches to annotated video. Webcam access happens in Python, not through a browser permission prompt. The video ends with an explicit message; restart the server to replay. Files are processed one frame per request, so wall-clock playback speed depends on inference performance. The tracker uses source FPS for file timestamps. Network streams are rejected. CPU inference is the default.

**Vision limits:** box-bottom coordinates are normalized into a schematic grid. There is no homography calibration, monocular depth model, ego-motion compensation, or physical distance/speed estimate. The speed card therefore says N/A. The image-space decision overlay is illustrative, not a braking recommendation. Camera cuts and crossings can cause ID swaps. The default corridor is manually assumed, not inferred from pixels. COCO-style weights do not contain dedicated auto/thela labels; use a custom trained detector whose class names match `backend/vision.py` to detect those classes distinctly. The camera adapter is included but was not end-to-end tested with hardware or model weights in the build environment.

## Algorithms

See [docs/ALGORITHMS.md](docs/ALGORITHMS.md) for equations, parameters, tradeoffs, and limitations. All animal/human differences are **configurable demonstration priors**, not empirically validated universal behavior claims. Humans can also move unpredictably.

## Project layout

```text
backend/engine.py       Tracking, uncertainty, grid, planner, decisions
backend/simulation.py   Six deterministic scenarios
backend/vision.py       Optional local detection adapter
frontend/               HTML, CSS, Canvas and JavaScript
server.py               Local HTTP API and asset server
requirements-vision.txt Optional dependencies
start.bat / start.sh     Launchers
tests/test_engine.py    Algorithm and HTTP tests
docs/                   Algorithms, judge guide and validation
.github/workflows/      GitHub test workflow
```

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Local engine status, mode, scenario catalog |
| `POST /api/reset` | `{ "scenario": "occlusion" }` |
| `POST /api/step` | `{ "dt": 0.1, "horizon": 3, "multiplier": 1, "memory": true, "corridor": 5 }` |
| `GET /api/export` | Last state and last 3,000 simulation history samples |

Numeric inputs are bounded; nonfinite values are rejected. Default bind address is loopback. This standard-library server is intended for a single local demo, not public production hosting. Vision export includes the last JPEG and tracks; simulation history is empty in vision mode. Files and camera data are not uploaded by the application.

## Test

```bash
python -m unittest discover -s tests -v
```

Tests cover class uncertainty, risk footprint, tracking velocity, identity through occlusion, expiry, memory ablation, stop/hysteresis, path bounds, scenario outputs, HTTP responses, validation, and origin checking. See [docs/VALIDATION.md](docs/VALIDATION.md).

## Put it on GitHub

Create an empty repository named `aura-offline-demo` in your GitHub account. From the extracted project folder:

```bash
git init
git add .
git commit -m "Add AURA offline risk reasoning demo"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/aura-offline-demo.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your account. Authenticate using your normal GitHub method; never put tokens in source files. Alternatively use GitHub Desktop to add this folder and publish the repository. Include hidden `.github` and `.gitignore` files. The included workflow runs tests after push.

**GitHub stores the project; GitHub Pages cannot run this Python backend.** For judging, run it on your laptop and share the repository as evidence of the implementation. A cloud-hosted deployment is not required for this offline demonstration.

## Troubleshooting

- `python` not recognized: install Python, or try `py -3` on Windows / `python3` on macOS or Linux.
- Port occupied: `python server.py --port 8001`, then open `http://127.0.0.1:8001`.
- Engine unavailable: check the terminal; launch through the server, not `file://`.
- Camera failure: close other camera apps; try `--source 1`; check OS permission for Python.
- Missing model: provide an existing local `.pt` file. Simulator works without any model.
- Optional package failure: use a clean Python 3.12 virtual environment and install before going offline.

## Attribution and licensing

Project-authored code is MIT licensed (see LICENSE). Optional Ultralytics software and weights have their own license terms; those are not covered by this project's MIT license. No third-party weights, dataset, road recording, or slide artwork is redistributed. See [Ultralytics licensing](https://www.ultralytics.com/license) before redistribution of a combined vision package.
