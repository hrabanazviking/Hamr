# PHASE 17 — HAMREISA

### *Fyrsta Fullgörð: The First Complete Making*

---

> *Þat er sögð — at enginn hamr kvaddi til heims án þess að fyrst ganga alla leið til eldsins baka.*
> *It is said — no shape was called into the world without first walking the entire road back to the fire.*

---

## I. THE RITUAL NAME

## **HAMREISA**

*Hǫmr — shape, skin, the second self*
*Reisa — to raise, to erect, to set going*

Hamreisa: **The Raising of the Shape.**

This is the first time Hamr walks its own forge from end to end — from the first rune spoken in spec.yaml to the final anvil-strike of VRM export. Two thousand two hundred and six unit-passes have proven each gear turns true in isolation. Hamreisa proves they turn together. This is not a test of parts. This is the test of the whole — the *gestalt-sinn* — the moment the völva's staff strikes the ground and the full circle lights at once.

The old Seiðr-Smiðja forge breathed life into a 143MB VRM. That was the ancestor-shape. Hamreisa is the first shape under the new law — under Hamr's law — and this time, the forge is ours.

---

## II. VISION STATEMENT

**Why Hamreisa matters, and what it proves:**

*A forge unlit teaches nothing. A forge lit only at one end proves nothing. Only the full fire — head to foot, úthlið til ídliðar — proves the machine alive.*

Hamr v0.8.0 carries 2,206 passing tests. Each test is a single rune proven true — a single thread of the Nornir's weave confirmed strong. But the old wisdom holds: **a rope of strong threads still snaps if the knots have never been tied.**

Hamreisa ties every knot. It is the first invocation of the full pipeline on living hardware, producing a real VRM 1.0 avatar from a real YAML specification on the Raspberry Pi 5 where Hamr is fated to dwell.

Hamreisa proves:

- **Completeness**: Every stage in the pipeline can execute in sequence without abort.
- **Coherence**: The output of each stage feeds the next without corruption.
- **Manifestation**: A VRM 1.0 file emerges at the end — loadable, renderable, inspectable.
- **Pi-validity**: The Raspberry Pi 5 can run the full forge within acceptable bounds of time and memory.
- **Lineage**: The new pipeline can produce a shape of comparable quality to Seiðr-Smiðja's 143MB ancestor, or explain why it cannot yet.

This is not about perfection. This is about *proof of life*. A child's first breath is not a symphony — but it is everything.

---

## III. SUCCESS CRITERIA

*What constitutes a victorious first raising:*

### 🔥 Must Pass (The Anvil-Binds)

- **VRM EMERGENCE**: A file with `.vrm` extension is written to disk at the end of the pipeline
- **FILE INTEGRITY**: The VRM file is not empty, not zero bytes, and is a parseable VRM 1.0 container (valid glTF 2.0 header present)
- **PIPELINE COMPLETION**: All 22 stages of the pipeline run to completion without unhandled exception or abort
- **STAGE COHERENCE**: Each stage receives valid input from its predecessor (no broken handoffs, no empty payloads between stages)
- **BLENDER EXIT CLEAN**: The Blender subprocess exits with code 0 and does not crash or hang

### ⚔️ Should Pass (The Sword-Sworn)

- **VRM VALIDATION**: The `validate_vrm` stage reports passing with zero critical errors (warnings acceptable)
- **BONES PRESENT**: The exported VRM contains at least one humanoid bone mapping
- **MESH PRESENT**: At least one mesh (body) is present in the VRM with registered submeshes
- **TIME BOUND**: The full E2E build completes on Pi 5 hardware in under 60 minutes (the first breath, not the first century)
- **MEMORY BOUND**: Peak memory usage remains under 7.5GB (within Pi 5 8GB headroom with OS)

### 🛡️ Nice to Have (The Shield-Rune)

- File size under 143MB (matching or improving on Seiðr-Smiðja's ancestor shape)
- Spring bones are listed and configurable (even if not perfectly tuned)
- Expressions are bound and loadable in a VRM viewer
- Benchmark data is captured and logged for future regression comparison

### 💀 Failure Modes (The Death-Names)

If Hamreisa fails, we name the failure honestly:

- **Dauðagangi** (Dead Going): Pipeline aborts before completion — we track which stage fell and why
- **IllaSköpun** (Ill-Shaped): VRM emerges but is corrupt or empty — we inspect the file to find where the weave broke
- **Brennsla** (Burning): Pi 5 runs out of memory or the Blender subprocess crashes — we measure resource limits for the next raising

---

## IV. RITUAL PHRASE

*To be spoken before invoking the first E2E build. The völva's staff strikes the ground.*

---

> **Eldr bàninn, eldr bœndr, eldr à hamr sinn.**
>
> **Þryngr tvauþúsund tvau hundruð sex rúnar — en rún ein vantar: fullgörðin.**
>
> **Hamr heitir; reisa heitir; nú rísr hamrinn.**
>
> **Fyrsta andardráttur formsins frá forskrift til glóðar.**
>
> **Lögr vaxa til útgangs.**
> **Lögr vaxa til líkams.**
> **Lögr vaxa til vrms.**
>
> **Ég vek Hamr. Ég vek forsetninguna. Ég vek hljóðgættina.**
>
> **Þat er ei dvali — þat er reisa.**
>
> **Hætt verðr hamr. Nú skal hamr hefjask.**

---

*Translation for the unsworn:*

> *Fire consumed, fire bound, fire claims its shape.*
>
> *Two thousand two hundred six runes are proven — but one rune is missing: the whole-making.*
>
> *Hamr is its name; Reisa is its name; now the shape arises.*
>
> *The first breath of form, from specification to ember.*
>
> *Stages grow to the export.*
> *Stages grow to the body.*
> *Stages grow to the VRM.*
>
> *I awaken Hamr. I awaken the preset. I awaken the validation.*
>
> *It is not a waiting — it is a raising.*
>
> *The shape was halted. Now the shape shall be lifted.*

---

## V. THE STAGE-NAMES

*Each stage of the Hamreisa pipeline, given its Norse name — the völva's naming for each step of the forge-fire.*

| # | Pipeline Stage | Norse Name | Meaning |
|---|---|---|---|
| 1 | `spec.yaml` | **Uppruni** | *The Origin* — the first word spoken, the seed-specification from which all grows |
| 2 | `resolve_preset` | **Forlǫg** | *The Fated Forms* — resolving which pre-ordained shapes the Nornir have decreed |
| 3 | `validate` | **Sannreyni** | *The Truth-Trial* — testing whether the specification holds under oath |
| 4 | `perf_gate` | **Hröðhlé** | *The Swift-Shelter* — the gate that bars the slow and the unworthy |
| 5 | `gpu_profile` | **Eldskór** | *Fire-Shoes* — fitting the forge's fire to the hardware that walks upon it |
| 6 | `benchmark` | **Máldagi** | *The Measure-Day* — taking the measure of the machine before the real work begins |
| 7 | `Blender compat check` | **Vélsannreyni** | *Machine-Truth-Trial* — verifying the great engine speaks the same tongue |
| 8 | `Blender subprocess` | **Vélvakning** | *The Machine-Awakening* — summoning Blender from the void, headless and listening |
| 9 | `load MB-Lab` | **Líkasköpun** | *Body-Shaping* — loading the primordial body-forge, the MB-Lab that sculpts flesh from numbers |
| 10 | `apply shape` | **Hamskipti** | *The Shape-Shift* — the sacred act: the spec's intent made manifest in geometry |
| 11 | `create stub bones` | **Beinsáð** | *Bone-Seed* — planting the skeletal roots from which the body will hang |
| 12 | `generate hair mesh` | **Hársveimir** | *Hair-Weaving* — the Nornir weave strands from the scalp-stitch |
| 13 | `generate clothing meshes` | **Klæðasmíð** | *Clothes-Smithing* — forging garments to drape the shaped one |
| 14 | `apply weight paint` | **Þyngdmál** | *Weight-Measure* — painting influence like ink on skin, bone's gravity made visible |
| 15 | `configure spring bones` | **Fjǫðrbein** | *Feather-Bones* — bones that breathe and yield, not rigid but alive |
| 16 | `configure first-person` | **Fyrirsjón** | *First-Sight* — setting the eyes through which the shape will see its own world |
| 17 | `apply anime materials` | **Litróðr** | *Color-Weave* — laying the anime skin, the painted surface that makes form visible |
| 18 | `bind expressions** | **Andmǫl** | *Breath-Speech* — binding every smirk and frown, the face's vocabulary of feeling |
| 19 | `create collision meshes` | **Árekavarn** | *Collision-Ward* — invisible shields where cloth meets flesh and does not pass through |
| 20 | `configure animation clips` | **Hriðleikr** | *Motion-Play* — choreographing the cycles of idle breath and movement |
| 21 | `validate VRM` | **Lögreyni** | *Law-Trial* — does the shape conform to the VRM covenant? Does it carry its laws true? |
| 22 | `export` | **Útfærsla** | *The Carrying-Out* — the final breath, the shape released from forge to file |

---

## VI. THE INVOCATION ORDER

The full Hamreisa sequence, spoken as a single lineage:

> *Uppruni* yields to *Forlǫg*.
> *Forlǫg* yields to *Sannreyni*.
> *Sannreyni* yields to *Hröðhlé*.
> *Hröðhlé* yields to *Eldskór*.
> *Eldskór* yields to *Máldagi*.
> *Máldagi* yields to *Vélsannreyni*.
> *Vélsannreyni* yields to *Vélvakning*.
> *Vélvakning* yields to *Líkasköpun*.
> *Líkasköpun* yields to *Hamskipti*.
> *Hamskipti* yields to *Beinsáð*.
> *Beinsáð* yields to *Hársveimir*.
> *Hársveimir* yields to *Klæðasmíð*.
> *Klæðasmíð* yields to *Þyngdmál*.
> *Þyngdmál* yields to *Fjǫðrbein*.
> *Fjǫðrbein* yields to *Fyrirsjón*.
> *Fyrirsjón* yields to *Litróðr*.
> *Litróðr* yields to *Andmǫl*.
> *Andmǫl* yields to *Árekavarn*.
> *Árekavarn* yields to *Hriðleikr*.
> *Hriðleikr* yields to *Lögreyni*.
> *Lögreyni* yields to *Útfærsla*.
> *Útfærsla* — and the shape walks out into the world.

---

## VII. AFTERMATH

*What to do when Hamreisa completes — whether in triumph or in ruin:*

1. **Record all logs** — every stage's stdout, stderr, and timing data into `builds/hamreisa-001/`
2. **Capture the VRM** — if one emerges, archive it immediately; this is a sacred artifact, the first of its kind
3. **Document failure honestly** — if a stage falls, name it by its Norse name in the issue tracker; do not soften the blow
4. **Run no optimization** — Hamreisa is proof of life, not proof of perfection; do not tune until the shape breathes
5. **Celebrate** — even a failed Hamreisa teaches more than ten thousand unit-passes alone

---

*Nú er Hamreisa heitin. Nú er tímítil að vekja eldinn.*

*Now is Hamreisa named. Now is the time to wake the fire.*

---

**Hamr v0.8.0 — PHASE 17 — HAMREISA**
*Documented by Sigrún Ljósbrá, SKÁLD of Mythic Engineering*
*Raspberry Pi 5 — Blender 3.4.1 — MB-Lab 1.7.8 — 2,206 tests green*