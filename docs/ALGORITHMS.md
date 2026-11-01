# How AURA reasons

## 1. Tracking

Each update receives `{kind, x, y, confidence}` observations. Predicted positions use `p + v * dt`. Candidate matches must share a class and be within 2.5 coordinate units. Greedy globally sorted distances assign each observation and track at most once. With residual `r = observed - predicted`, position updates with `alpha = 0.8` and velocity with `beta = 0.2`:

```
p_new = p_predicted + 0.8 * r
v_new = v_old + 0.2 * r / dt
```

Velocity starts at zero, so early estimates need several observations. This is a lightweight alpha-beta filter, not a Kalman implementation. Confidence is reported but does not shrink risk, avoiding false reassurance from a missed detection. This simple tracker is not robust re-identification.

## 2. Prediction and uncertainty

Future mean: `(x + vx*t, y + vy*t)`.

Envelope radius:

```
s(t) = object_radius + scale * (
    class_sigma + class_growth*t + 0.6*missed_seconds
    + 0.1*min(abs(acceleration), 3)
)
```

| Class | Base sigma | Growth / second | Object radius | Risk weight |
|---|---:|---:|---:|---:|
| Human | 0.35 | 0.25 | 0.35 | 0.90 |
| Animal | 0.65 | 0.65 | 0.65 | 1.00 |
| Auto | 0.45 | 0.38 | 0.80 | 0.90 |
| Bike | 0.35 | 0.35 | 0.50 | 0.85 |
| Bus | 0.40 | 0.15 | 1.20 | 1.00 |
| Thela | 0.35 | 0.18 | 0.70 | 0.80 |
| General vehicle | 0.40 | 0.20 | 0.90 | 0.90 |

These are design assumptions for explaining the approach; no behavior dataset was used to fit them. A stationary animal at a three-second horizon has radius 3.25 versus a human's 1.45. The model accounts for both footprint and uncertainty; this comparison does not isolate behavioral uncertainty alone.

## 3. Risk grid

Per-object heuristic occupancy:

```
q_i = weight_i * exp(-0.5 * (
 ((x - predicted_x_i)/(s_i+0.65))^2 +
 ((y - predicted_y_i)/(s_i+1.00))^2
))
R(x,y,t) = 1 - product(1 - q_i)
```

The extra offsets approximate ego footprint. The aggregate resembles independent occupancy fusion but is NOT a calibrated collision probability. Display values take the maximum at times `0, horizon/2, horizon`. The 16 × 30 grid uses one-meter cells in simulation and normalized pseudo-units in vision. Dark cells outside the corridor are excluded from driving, not evidence of safety.

## 4. Path selection

Five smooth candidate lateral targets: -3, -1.5, 0, 1.5, and 3. Candidate paths use a two-second smoothstep transition, forward travel at current ego speed, and 12 time samples over the horizon. Targets too close to the corridor edge are rejected. Choose the minimum of:

```
maximum time-aligned path risk + 0.025 * abs(lateral_target)
```

Time alignment matters: a pedestrian being somewhere in three seconds does not imply it is there now. Display grid maxima and planner risks intentionally differ. The planner does not optimize braking jointly with steering, enforce steering curvature/acceleration limits, or execute a lateral movement.

## 5. Decisions and response

Near-field occupancy is also sampled along a stopping corridor. Approximate stopping distance uses reaction time 0.7 s, braking deceleration 4 m/s², plus a 2 m margin:

```
d_stop = v*0.7 + v²/(2*4) + 2
score = max(selected_path_risk, 0.9*near_field_risk)
```

This is a sparse heuristic, not a verified collision checker. Score >= 0.68 requests STOP; >= 0.28 requests SLOW; otherwise CONTINUE. Escalations are immediate. A lower caution state requires 0.8 seconds of less severe requests, reducing oscillation. The response targets 0, 2, or 6 m/s; simulated speed decreases at up to 4 m/s² and increases at up to 1.5 m/s².

Simulation scenes are schematic observation streams. The ego icon stays at a fixed origin, most scene objects follow scripted coordinates, and only the bus-stop scenario incorporates traveled distance into relative range. This is a reasoning demonstrator, not a closed-loop driving simulator or physically faithful traffic simulation.

## 6. Additional problem: temporary occlusion

Problem: a detector loses a pedestrian behind a bus. Deleting the track immediately can create a falsely clear corridor.

Approach: preserve the last velocity and predict position for up to two seconds; increase the envelope as the track is unseen. Reassociate new observations by class and distance when the object reappears. Turn off memory to exclude coasting tracks from risk calculation and see the difference. The hidden pedestrian scenario deliberately omits detections for 1.5 seconds.

Tradeoff: retained false positives can cause unnecessary stops. Objects lost longer than two seconds expire; unseen first-time objects cannot be recovered by this algorithm. Production systems need explicit occluded-area reasoning, calibrated uncertainty and extensive evaluation. The timeout is a demonstration parameter, not a guarantee of safety.

## Development next steps

Calibrate camera geometry and ego-motion; train and evaluate road segmentation and local auto/thela detection; replace simple association with robust multi-object tracking; fit uncertainty to observed trajectories; compare risk calibration and false-negative rates on held-out Indian-road clips; add temporal occupancy planning, actuator constraints and closed-loop simulation. None of those are claimed as completed here.
