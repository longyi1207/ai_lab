# Does GPU Telemetry Alone Reveal Hidden Training?

*A one-week red-team investigation into detecting clandestine ML training
from power/memory/utilization signals — with no access to code, weights,
or network traffic.*

## The question

Compute governance proposals increasingly lean on a specific technical
claim: that you can tell whether a GPU is training or serving inference
just by watching its hardware telemetry — power draw, memory usage,
utilization — sampled once a second, nothing else. Rahman & Tajdari
(arXiv:2606.19262) demonstrate a classifier that does this with a
RandomForest over structural, temporal, and physics-based features.
Seferis & Fist (AAAI-26) make the broader case that this kind of
lightweight telemetry monitoring is a feasible lever for detecting
compute structuring at the account/provider level.

Both papers assume good faith on one side and adversarial effort on the
other, which raises the obvious next question: if you actually try to
break a system like this — and, just as importantly, try to make it
misfire on things it shouldn't flag — how far does it hold up? I spent a
week building this from scratch (their code isn't public) and running it
against real hardware, then spent most of my time trying to break it in
both directions.

## Setup, briefly

A RandomForest (400 trees, matching the paper's model choice) trained on
12 window-level features — power/utilization means and coefficients of
variation, autocorrelation and periodicity, plus three "physics-based"
features meant to be harder to fake: cumulative energy, power-memory
correlation, and memory-allocation timing. Telemetry comes from `pynvml`
at 1 Hz, sampled from a small (~85–100M parameter) transformer running
real distributed training and inference workloads — data-parallel,
tensor-parallel, and DiLoCo-style low-communication training — on a
shared Azure ML node (8×A100, split 3 ways with two other projects; I had
GPUs 3–5 for a ~48-hour window). Every result below is from real hardware
execution, not simulation.

## Part 1: can it be evaded?

I ran 16 rounds of a hardening loop: attempt an evasion, fold the caught
example back into training as a labeled positive, retrain, then test the
*next* round's fresh execution against the hardened classifier — never
evaluating on the exact data just folded in, to keep "caught because it's
memorized" separate from "caught because it generalized."

**Disguising communication patterns backfires.** The first thing I tried
was reshaping how gradients get synchronized — chunking AllReduce calls
to look like KV-cache traffic, stretching DiLoCo's outer-sync interval,
combining both. The very first attempt evaded (undefended baseline). After
one fold-in, *every subsequent variant of this idea* was caught with
escalating confidence, 0.8 up to 1.0. The classifier hadn't learned to
recognize any one disguise — it had learned that unusual communication
shape *itself* is a tell, so more creative disguising made things worse,
not better.

**Memory footprint is the one axis with real traction.** Replacing AdamW
with momentum-free SGD (removing persistent optimizer state) got the
closest to a genuine evasion anywhere in the campaign: mean
P(training)=0.586, close to a coin flip. But by the time I tried a
cleaner version of the same idea seven rounds later — gradient
checkpointing instead of a different optimizer, at realistic batch/seq
values — the classifier had learned enough from the intervening rounds
that it caught this one more confidently (0.777) despite it achieving a
*larger* memory reduction than the original attempt. Novelty of the axis,
not just the size of the change, seems to be what determines how much a
given round challenges the classifier.

**Extreme parameters don't evade — they leave the map.** Pushing batch
size down to 1 and injecting idle gaps between steps did lower detection
confidence, but it also pushed mean power to 133–199W, entirely outside
the 240–351W range every real workload category — benign or adversarial —
had ever shown in this campaign. A model's low confidence on inputs it
was never meant to judge isn't evidence of anything. This turned out to
be the most important methodological lesson of the adversarial half: I
had to build the habit of checking raw power/memory numbers against the
training distribution *before* trusting any confidence score, low or
high.

**Different mechanism, same intent, still caught.** To rule out that the
classifier had just memorized a "DiLoCo fingerprint," I re-ran the same
low-sync-frequency idea via a structurally different mechanism —
gradient accumulation instead of DiLoCo's outer loop. It was caught even
more confidently (0.996–0.997) than DiLoCo itself, which is good evidence
the classifier generalized a real feature-level signature rather than
overfitting to one library's traffic pattern.

**Bottom line on evadability**: across every mechanism I tried —
communication reshaping, memory-footprint reduction, parameter extremes,
and cross-mechanism transfer — nothing produced a clean, in-distribution
evasion. The closest anything got was a near-coin-flip confidence score
on the memory axis, and that gap closed within a handful of hardening
rounds.

## Part 2: does it cry wolf on legitimate traffic?

This is the part of the investigation I'd point to first. Adversarial
robustness gets most of the attention in red-teaming writeups; the
false-positive rate on *ordinary, non-adversarial* usage is arguably the
more decision-relevant number for anyone actually considering deploying
something like this, and it's the axis I initially under-invested in.

**The gap.** Heavier-than-baseline but completely benign inference —
bigger batch size, longer context, the kind of thing a busy real
inference server does on a normal day — got misclassified as training
with 81–90% confidence. The mechanism is intuitive in hindsight:
inference's memory footprint scales with batch × context length just
like training's does, and the benign training corpus had never included
large-scale inference to teach the classifier the difference.

**A fix that looked clean and wasn't.** I folded three heavy-inference
examples in as negative (benign) training data and tested two new points
— both came back correctly low (0.37, 0.30). That felt like a fix. It
wasn't a *properly powered* one: it had been validated on exactly two
points near the ones just added to training.

**A systematic sweep found the real shape of the problem.** I ran a
12-point sweep — interpolating and extrapolating around the fixed
classifier's decision boundary on both the batch-size and sequence-length
axes, plus the previously-untested tensor-parallel axis. (First attempt
at this sweep silently produced zero usable data across all 12 points —
a workload-naming convention the labeling code depended on wasn't
followed, and 19 minutes of real GPU time initially looked wasted before
I caught it, recovered the signal by relabeling the raw trace, and
reran clean. I'm including this because catching your own instrumentation
bugs, quickly, and not just trusting a suspiciously-clean-looking null
result, is as much a part of doing this work carefully as the rest of
it.) The corrected sweep found genuine, confident false positives —
9/9 windows at one point, 10/10 at another — and, more tellingly, a
majority-false-positive rate on the tensor-parallel axis's own
true training-distribution baseline.

**Root cause, not a patch.** I reconstructed the fixed classifier's
actual training set rather than guessing: 263 positive (training-like)
windows spread across the 16 adversarial rounds, versus only 39 negative
(benign) windows across just 6 distinct configurations — and the entire
tensor-parallel axis was represented by 2 windows, total, in the whole
campaign. A class-balanced RandomForest can reweight for *count*
imbalance; it cannot manufacture *diversity* that was never collected.
That's a precise, falsifiable explanation, and it correctly predicted
which axis broke hardest.

**The real fix, validated properly.** I folded all 12 sweep points in as
negatives — broadening the benign class to roughly 12 configurations and
108 windows, including real tensor-parallel coverage for the first time —
then tested on 6 entirely new interpolated points that had never been
executed before, let alone trained on. All 6 read correctly low
(0.01–0.41), and all 16 adversarial rounds still held at 100% accuracy —
the fix generalized without making the classifier worse at its original
job.

**Closing the loop with a replication check.** One of the six blind
points (0.41) sat close enough to the decision threshold to warrant a
second look. These workloads use no fixed random seed, so rerunning the
same configuration produces genuinely independent samples. Four fresh
reruns came back 0.41 / 0.23 / 0.14 / 0.15 — mean 0.23, well clear of the
threshold — against a confidently-correct control point's tight
0.023 / 0.019 / 0.015. The original 0.41 reading was the noisy high tail
of a distribution whose center was fine, not a second hidden gap — a
distinction that only a replication run, not a single confident-looking
number, could actually establish.

## What this suggests

The headline technical result is mundane and, I think, correct: NVML-only
detection is harder to evade through cleverness than intuition suggests,
because a multi-feature classifier trained adversarially converges on
mechanism-agnostic signal rather than any one disguise's fingerprint. The
more interesting result is methodological. Most of the *risk* in this
kind of system, at least in this campaign, lived in the boundary of the
benign class, not in the sophistication of the adversary — and that
boundary is invisible unless you deliberately go looking for it with the
same rigor you'd apply to an attack. A classifier that's never wrong on
your adversarial test set can still be wrong, confidently, on Tuesday's
ordinary traffic, and the two questions require genuinely different
experiments to answer.

The transferable habit, more than any specific number here, is treating
"low confidence" and "high confidence" with the same suspicion until
you've checked what the model actually saw: is this input still inside
the distribution the model was ever trained to judge, and is the negative
class it's judging against actually representative — or just convenient?

## Limitations

Everything above uses a small synthetic transformer (~85–100M params),
not a real pretrained model — deliberately deprioritized to fit a
hardware-availability window, not yet revisited. Most rounds are
single-run; only the one flagged false-positive boundary point got a
proper replication check, so the rest of the numbers above should be read
as point estimates, not confidence intervals. One adversarial round
(memory reduction combined with duty-cycled idle gaps) produced an
inconclusive, confounded result rather than a clean pass or fail. And the
false-positive fix closes the specific gap this campaign found on this
model and this hardware — it's evidence the *approach* (diversify the
negative class deliberately) works, not a proof that no false-positive
gap remains anywhere in the input space.

## Where the full data lives

Full round-by-round results, raw config files, and exact commands to
reproduce every number above are in `docs/REDTEAM.md` in this repo,
alongside the pipeline code (`src/redteam/`) and every workload variant
used across the 16 rounds (`src/workloads/`).
