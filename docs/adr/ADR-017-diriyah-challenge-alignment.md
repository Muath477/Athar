# ADR-017: Aim Round 1 at the Diriyah wall damage challenge

- Status: Accepted (pending team review)
- Date: 2026-11-18

## Context

The Culture and Heritage track lists four challenges. Two are close to Athar:

- **Detecting and mapping damage to mud walls** (Diriyah Gate Development Authority). At-Turaif walls are damaged by visitors and weather; inspection is manual and infrequent, and drawing damage maps takes specialists a long time. The challenge asks for an AI agent that identifies damage types (cracks, plaster loss, moisture erosion), proposes a specific treatment for each, and lists the materials and tools. Sensors are optional. Visitor behaviour on cameras is out of scope. Judging: accuracy against specialists, a single readable map with a clear colour key, ease of expert correction before approval, and blurring of faces.
- **AI to strengthen the protection and oversight of cultural heritage** (Heritage Commission). Judging: accuracy and few false alarms, early detection, scale across many sites, impact on decisions.

The Round 1 build covered change detection against a baseline and pins on a 3D model. It had no treatments, no materials, no plaster-loss type and no map in the conservation sense, and it could not say anything about a wall until a baseline existed.

## Decision

Submit Athar under the Diriyah challenge and add what its criteria ask for:

1. A damage map from a single photo: rectify the wall, split it into a grid, classify each cell (ADR-019).
2. A detector port so the map can come from Claude or from a ready-made model behind an HTTP endpoint (ADR-018).
3. A treatment catalog that maps each damage type and severity to steps, materials per m², tools and sources, and a plan that scales materials by the damaged area (ADR-020).
4. Expert correction per cell and approval, with the model's original answer kept so accuracy against the expert is measured continuously.

The visitor flow, verification gate and 3D pins stay. They become the way the authority gets frequent photos between expert surveys, which also answers the Heritage Commission criteria on scale and early detection.

## Alternatives

- Stay on the Heritage Commission challenge: broader, but Athar covers one kind of threat and its criteria reward breadth we do not have in three days.
- Replace the visitor flow with the map flow: loses the part that makes monitoring frequent and cheap.

## Consequences

- The pitch leads with the map and the treatment plan; the visitor story is the scale argument.
- The treatment catalog is a draft until a conservator reviews it. The UI says so on every plan.
- Accuracy is reported against expert-approved maps, so the team needs real wall photos and an expert (or mentor) to approve maps before demo day.
