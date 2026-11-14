---
type: page
order: 42
slug: proof
title: Proof
kicker: Proof
headline: What I have done, and what you can check before we talk.
description: Field work from thirteen years in operations, a published audit of 2,708 marketplace claims, and deterministic diagnostic software with 9,966 automated tests.
subject: Question on the proof
cta: Ask for a walk-through
published: 2026-11-09
updated: 2026-11-14
---
## Field work {: #track-record }

- **Melbourne, 2022 to 2024.** As Outbound Leader at AGCO Corporation, led the warehouse-system changeover of a 50,000-SKU distribution centre with a team of 20. Trained 23 operators on RF scanning on the floor, retired the paper workarounds, and stayed through stabilization; order processing time fell about 20%.
- **Cross-border e-commerce, 2020 to 2022.** Ran a USD 30M cross-border P&L and freed about USD 5M of inventory.
- **Three-site logistics, 2018 to 2020.** Ran operations across three sites with about 100 people and a USD 15M budget.
- **Retail planning, 2016 to 2017.** Led a team of 15 planners supplying more than 200 stores.
- **Earlier planning roles, 2013 to 2016.** Analysed a USD 100M inventory position, and identified about USD 2M a year of savings during a warehouse-system implementation.
- **On one floor walk.** Traced mixed, short and damaged orders to a per-operator productivity bonus, retired the metric and measured customer satisfaction instead.

## Published audit you can re-run {: #sample-audit }

- **[When "not received" means late](../not-received-but-delivered/).** A forensic triage of 2,708 "not received" claims on delivered orders in a public Brazilian marketplace dataset: 1,542 (57%) were written on or before the recorded delivery day, 73 sat at flagged sellers, and 1,093 had no clear cause in the record. The Python code and its tests are public and re-runnable.

## Built systems

I build my own diagnostic and planning tools so I do not arrive on a client's floor with a blank spreadsheet. None of them is in commercial production at a client yet; what they prove is how I translate operational physics into tested software before touching a live system:

- **Inventory and replenishment engine:** 9,966 automated tests in Python, counted on 14 November 2026. Its decision cards set the engine's recommendation beside the operator's own play and the status quo, and a stock spreadsheet goes from intake to a change that waits for a cryptographically signed approval and can be rolled back.
- **Receiving kit:** open source under the MIT licence, with 1,079 tests counted on 25 October 2026.
- **Field kit:** 1,187 passing tests on 20 October 2026. It checks an event log against the five-column contract (case, activity, timestamp, who, where) before any analysis runs, and its integrity guards catch a purchase-order line repeated by a one-to-many join, receipts held in blocked stock that do not balance, and negative stock; each guard is tested against a planted defect.
- **Weightlifting planning application:** a full-stack TypeScript monorepo with about 1,332 unit tests, 31 integration tests on an embedded PostgreSQL database and an adversarial review agent written into the repository. Building it for a coach left me a field postmortem on adoption from the builder's side: even when software leaves the expert full editorial control, measuring exactly what they used to judge by eye can make them refuse it.

The rule I build to:

<ol class="flow">
<li><strong>Check the extract before the math.</strong> Run silent corruption probes on the raw tables: one-to-many join fanout, negative or orphaned stock, un-netted in-transit lots, and unit-of-measure drift. <span class="flow-stop">If a number fails, nothing is written to the live system.</span></li>
<li><strong>Stage three plays in draft.</strong> Put the engine’s recommendation, the operator’s own adjustment, and the status quo side by side in a draft stage with their working-capital and service-level trade-offs.</li>
<li><strong>Sign off or override with a reason.</strong> The buyer or supervisor approves, modifies, or rejects the draft card; the decision and its reason are logged before execution.</li>
<li><strong>Keep the way back.</strong> Every approved change carries a rollback path and a 90-day check against the floor baseline.</li>
</ol>

The code is on [GitHub](https://github.com/esstipi-debug).

## Writing

- Two field notes, [*The Smith and the Tailor*](../the-smith-and-the-tailor/) and [*Nobody Pays for Being Wrong*](../nobody-pays-for-being-wrong/), and nine short answers, among them [why inventory records do not match the shelf](../why-inventory-records-do-not-match-the-shelf/) and [why people follow the system when it is wrong](../why-people-follow-the-system-when-it-is-wrong/).
- [*The Deployment Chasm*](../the-deployment-chasm/), a manuscript on why enterprise and supply-chain systems fail between the contract and the floor.
