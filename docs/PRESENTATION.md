# AURA: judge walkthrough and questions

## 3-minute walkthrough

**0:00–0:30 — Problem and scope.** “On an unmarked road, lane-following alone is insufficient. This prototype reasons about road users and the space they might occupy. The ready-to-run mode uses synthetic detections so that the same scenarios can be reproduced offline.”

**0:30–1:00 — Show the pipeline.** Select Unstructured street. Point to an ID and predicted motion. “Observations enter a lightweight tracker. Behavior rules and class-dependent uncertainty expand the predicted space. The planner checks candidate paths and outputs continue, slow or stop.”

**1:00–1:40 — Explain the risk grid.** Select Human vs animal. Pause. Change the horizon to five seconds and press Step. “The animal prior has faster uncertainty growth. A broader risky region represents uncertainty about future movement, not merely the current bounding box. These parameters are illustrative and require data validation.”

**1:40–2:20 — Additional algorithm.** Select Hidden pedestrian. Resume; pause between 3.0 and 4.5 seconds. Point to the occluded track and toggle memory. “Not seeing an object is not the same as knowing it has left. We coast the track for a short window and expand uncertainty. Disabling memory shows the less cautious baseline.”

**2:20–2:45 — Response.** Select Clear road, resume, and show CONTINUE. Compare the crossing or stopping-bus scenario. The action changes speed targets; the ego speed card shows simulated braking/acceleration.

**2:45–3:00 — Offline proof.** Disable Wi-Fi on the demo laptop. Switch scenarios. Explain that the browser and Python engine are both local. Optional vision uses model weights installed beforehand.

## Questions judges may ask

**Is this real AI?** The default simulator demonstrates the reasoning algorithm. The optional vision adapter runs a learned YOLO detector locally. The prediction, behavior and decision stages use explicit models and rules; do not call them a trained end-to-end neural policy.

**Is an animal always more dangerous?** No. The scenario compares configured priors. Risk also depends on distance, velocity, size, horizon and overlap with the vehicle path. Human unpredictability is possible too.

**How does it work without cloud?** Static assets are served by the laptop; all tracking, grid and planner computations run in local Python. Optional neural inference runs on the laptop CPU. Model and package downloads happen before offline use.

**What is the added algorithmic contribution?** Integration of class-dependent uncertainty with time-aligned path scoring and occlusion memory, plus a controlled on/off comparison. Do not claim the underlying algorithms were newly invented.

**Does it detect all six classes from video?** Not with generic weights. Auto and thela are simulated; dedicated real detection requires custom data/weights. The detector adapter supports those class names once such a model is supplied.

**Does it understand drivable road from pixels?** Not yet. The simulation has a known corridor; vision uses a manual approximation. Learned segmentation and camera calibration are future work.

**Is the risk percentage a crash probability?** No. It is a 0–100 normalized heuristic occupancy risk score.

**Can this drive a car?** No. It is a decision visualization and software prototype with simulated longitudinal response, without real control hardware or safety validation.

**How was it tested?** Algorithm and HTTP tests verify tracking, class envelopes, memory behavior, scenario outputs and API validation. The browser interface was exercised. Camera inference needs separate testing with your actual weights and footage.

**Do all existing autonomous systems require constant cloud?** No. Avoid that blanket comparison from the slides. Present offline operation and unmarked-road focus as AURA design goals without claiming that all other systems depend on cloud or lane markings.

## Before leaving for the venue

- Run the app once on the actual laptop. Keep the ZIP and extracted folder locally.
- Use the simulator if model setup has not been verified; never pretend it is live video.
- Verify the offline demonstration with Wi-Fi disabled.
- If using vision, check packages, local weights, footage and camera permission beforehand.
- Keep the terminal running and use one browser tab.
- Upload source to GitHub beforehand; a repository link is not the running backend.
