---
type: page
order: 30
slug: proof
title: Proof of work
headline: What I have done, and what you can check
kicker: Proof
description: A warehouse-system changeover, an audit anyone can re-run, the bonus that made broken orders, the systems I build and a one-page plan.
subject: What we're seeing
published: 2026-11-09
updated: 2026-11-14
---
## Track record {: #track-record }

**Outbound Leader, AGCO Corporation, Melbourne, 2022-2024.** A 50,000-SKU distribution centre through its warehouse-system changeover. I closed down the legacy system and stood up its replacement, with a team of 20 and 23 operators trained on RF scanning, and I stayed on the floor through hypercare until the shortcuts died. By my estimate, order processing time fell about 20%. The job mixed the desk and the floor: forklift, picking and packing, and dispatch with the carriers.

Before that: planning for more than 200 stores, a three-site logistics operation, a USD 30M cross-border e-commerce P&L and a USD 100M inventory position, across Chile, Argentina and Australia. Those employers are described, not named, under confidentiality.

## An audit anyone can re-run {: #sample-audit }

On a public marketplace dataset, I put "not received" reviews on orders marked delivered against the delivery record: 57% were written on or before the recorded delivery day. They describe late orders, not suspect customers. The method, the code and its limits are published. [Read the audit](../not-received-but-delivered/).

## A bonus that manufactured broken orders

On a gemba walk I traced mixed, short and damaged orders to a per-operator productivity KPI tied to a bonus. I retired the metric and measured customer satisfaction instead, as zero complaints and response time. The fix was the incentive, not the software.

## Systems I build

Prototypes: none of them runs a client's operation yet.

- A deterministic inventory-planning engine, with 9,966 automated tests counted on 14 November 2026. Its decision cards set the engine's options beside the operator's own play and the cost of doing nothing, and it takes a stock spreadsheet from intake to a change that waits for a named person's signature and can be undone.
- A weightlifting-periodisation app, a TypeScript monorepo with about 1,332 unit tests, 31 integration tests on an embedded PostgreSQL database and an adversarial review agent written into the repository. Building it for a coach taught me adoption from the builder's side: even when software leaves the expert full editorial control, measuring exactly what they used to judge by eye can make them refuse it.
- A warehouse-receiving kit, open source under the MIT licence, with 1,079 tests counted on 25 October 2026.
- A field kit for deployment work, with 1,187 passing tests on 20 October 2026.

The rule I build to:

<ol class="flow">
<li><strong>A model proposes.</strong> A forecast, a reorder, a match between two records.</li>
<li><strong>Deterministic code checks every number.</strong> Same input, same answer, and the check is written down. <span class="flow-stop">If a number fails, nothing is written: the location goes back to the floor for a recount.</span></li>
<li><strong>A named person signs.</strong> Nothing changes a system of record without a signature.</li>
<li><strong>The record changes.</strong> The proposal, the check and the signature are kept together.</li>
</ol>

The code is on [GitHub](https://github.com/esstipi-debug).

## Writing

[Field notes and short answers](../#field-notes) on what happens to systems after go-live, each with one mechanism and one source. [*The Deployment Chasm*](../the-deployment-chasm/), a manuscript on why enterprise technology that works in the plan fails on the floor.

## One-page plan

The [client onboarding plan](../files/client-onboarding-plan.pdf) (PDF, one page): how I run the first weeks of a deployment, from the floor to the handback.
