# 01 · Research and benchmarking

Written 2026-11-16. Links were found by web search on that date; claims about each tool are limited to what its own page or paper states.

| Tool | What it does | Who uses it | What it lacks that Sadu covers |
|---|---|---|---|
| [Arches](https://www.archesproject.org/what-is-arches) (Getty Conservation Institute + World Monuments Fund) | Open-source platform for heritage inventories and management: records, maps, condition data. | National and city heritage agencies, NGOs. | No visitor capture flow, no automatic change detection, no 3D pinning. A natural system of record to integrate with later. |
| [EAMENA](https://eamena.org/) (Oxford, Leicester, Durham) | Database of endangered archaeological sites in the Middle East and North Africa, built on Arches, mostly from satellite and aerial imagery. | Researchers, heritage authorities in MENA. | Site-level, remote-sensing view; does not see facade-level cracks or graffiti, no ground photos from visitors. |
| [Monument Monitor](https://discovery.ucl.ac.uk/id/eprint/10153800/9/Brigham__thesis.pdf) (UCL with Historic Environment Scotland) | Visitors at 20 sites sent photos of specific features through messaging and social media; ML used to classify and segment issues. | Historic Environment Scotland conservation staff. | Closest prior work. Photos arrive through social channels with no guided angle, no baseline alignment, no evidence-linked confidence label, no 3D twin. The thesis notes crowdsourced data suits coarse features better than fine detail, which supports our overlay and "named facade" choices. |
| [Heritage Eye](https://calvium.com/project/heritage-eye/) (Calvium for Bristol City Council) | App for officers and community groups to survey buildings on the Heritage at Risk register; simple photo + comment form for the public, linked to the council's GIS. | Council heritage officers, civic societies. | Manual surveys; no AI comparison, no verification step, no incentive for casual visitors. |
| [FixMyStreet Platform](https://fixmystreet.org/overview/) (mySociety) | Open-source citizen problem reporting with map pins routed to the responsible body. | UK councils and others. | Generic street issues, a photo and a pin with no prior state or severity; shows the routing and status-feedback pattern we copy. |
| [CyArk](https://www.cyark.org/whatwedo/documentation/) | High-detail 3D documentation (laser scanning, photogrammetry) of heritage sites, open archive. | Heritage bodies, researchers. | One-time expert capture; no continuous monitoring after the scan. Sadu reuses the idea of a 3D twin and adds change over time. |

## What this tells us

- Every competitor either has **capture** (Monument Monitor, Heritage Eye, FixMyStreet) or **a model of the asset** (Arches, CyArk), not both, and none verifies a crowd photo against a baseline before it reaches the authority.
- Monument Monitor's experience is the main warning: unguided visitor photos vary too much for fine detail. Guided capture and facade-level granularity are must-haves, not polish.
- Status feedback to the reporter (FixMyStreet) keeps contributors engaged; the Sadu Passport covers this.

## Feature list

| Must have (Round 1) | Nice to have (Round 2 or later) | Skip |
|---|---|---|
| Guided capture with baseline overlay | Heat map of facade damage | AR anchoring |
| Facade identification from GPS + heading + image | Timeline slider per spot | Native apps |
| Baseline alignment + difference + LLM judgment | Restoration PDF report | Training a custom model |
| Evidence-linked confidence labels, Verifier gate | National map with region packs | Social login, gamified leaderboards |
| 3D model with pins and evidence panel | Export to Arches (system of record) | Satellite imagery |
| Expert review queue | Offline queueing in the PWA | Visitor-to-visitor social features |
| Verified story with sources + Arabic audio | Push notifications for missions | |
| Coverage gaps and mission dispatch | YOLO segmentation masks on the evidence panel | |
| Sadu Passport (anonymous) | | |

## Update 2026-11-18: wider comparison for the Diriyah challenge

| Tool | What it does | What it lacks that Athar covers |
|---|---|---|
| [Scopito](https://www.g2.com/products/scopito/reviews) | Cloud platform to store, annotate and report inspection photos with AI fault detection; priced per asset or inspection, white-label option; built for power lines, solar, wind and buildings. | Not built for earthen heritage or Arabic; stops at annotation, no treatment or materials. |
| [T2D2](https://enr.com/articles/56644-ai-driven-facade-inspection-system-deployed-for-historic-building-preservation) | AI facade inspection from drone photos and video, used on historic buildings. | Needs drone campaigns; early versions confused shadows of repaired cracks with open cracks, the same risk Athar faces on sunlit mud walls. |
| [Iconem](https://www.archpaper.com/2019/04/iconem/) | 3D documentation of endangered sites with drones, photogrammetry and AI. | One-time expert campaigns, not continuous monitoring or treatment planning. |
| Heritage Commission "بلاغ أثري" ([Okaz](https://www.okaz.com.sa/local/na/2258944)) | Official channel for reporting encroachment, digging and artefact trade, alongside field patrols. | Covers violations, not slow condition decay of walls; no image analysis. |
| Research: [Kasbah of Algiers crowd-sensing CNN](https://data.mendeley.com/datasets/zwshr65gnc/2), [Fujian Tulou earthen crack detection](https://mdpi.com/2079-6412/15/10/1156), [ABECIS](https://arxiv.org/abs/2206.09742) | Phone or drone photos classified for crack, spall, efflorescence, mould; open-source crack segmentation. | Proof that the detection part works; none is a product with expert review and treatment plans. ABECIS reports that human verification on top of the model gives the most accurate result, which is Athar's design. |

The interactive comparison, stress test and UML gallery are in the published page linked from the pull request. The UML source is [11-uml.md](11-uml.md).
