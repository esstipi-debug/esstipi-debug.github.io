---
type: page
order: 42
slug: proof
title: Proof
kicker: Proof
headline: What I changed, checkable before we talk.
description: Field work from thirteen years in operations, a published audit of 2,708 marketplace claims, and deterministic diagnostic software with 10,483 passing tests.
subject: Question on the proof
cta: Ask for a walk-through
published: 2026-11-09
updated: 2026-11-16
---
## What each claim rests on {: #evidence-map }

<!-- plate: backing -->

## Field work {: #track-record }

Supply chains break across boundaries: a buying rule locks up cash, a cutover pushes teams onto spreadsheets, or a bonus manufactures bad shipments. Here is what I changed across thirteen years in operations, planning and consulting, and why unarchived field diagnoses were consolidated into [*The Deployment Chasm*](../the-deployment-chasm/) and the checks below.

- **System changeover without floor bypass (AGCO Corporation, Melbourne, 2022 to 2024).** Outbound Leader, split between the desk and the floor: picking, packing and the carriers. Through the full cutover of a 50,000-SKU distribution centre with a team of 20, I closed the legacy warehouse system and opened Manhattan Associates, trained 23 operators on RF scanning, and stayed on shift until the workarounds ended. Order processing time fell about 20% (a shift estimate without retained logs).
- **Working capital and demand rules under rapid scale (cross-border e-commerce, 2020 to 2022).** Owned a USD 30M P&L spanning direct consumer sales and wholesale. Through 300% annual growth, replaced judgement buffers with aggregate statistical demand forecasting and wrote the operating procedures that kept volume moving, freeing about USD 5M of inventory.
- **Multi-site reporting and replenishment control (Chile and Argentina, 2016 to 2020).** Ran a USD 15M budget across three logistics sites and about 100 people, replacing lagging weekly packs with daily operational reporting that every site planned from. Earlier led 15 planners supplying more than 200 retail stores (holding part of the role remotely from Sydney), building forecasting and replenishment models to balance stockouts against inventory while automating financial reports.
- **Cost allocation and pre-cutover savings (2013 to 2016).** Analysed a USD 100M inventory position with cost-allocation models and cycle-count controls so the business could see where operating expense actually sat, and identified about USD 2M a year in purchasing and logistics savings alongside floor procedures for an earlier warehouse-system rollout.
- **Cross-industry diagnostics and incentive repair (since 2013).** Across more than seven independent consulting engagements in warehousing, retail, e-commerce and manufacturing, I built process maps, KPI dashboards and floor procedures. On one floor walk, tracing mixed, short and damaged orders back to a per-operator productivity bonus showed how local metrics break downstream quality; I retired the bonus metric and measured customer satisfaction through zero complaints and response time instead. Individual client archives from that consulting work were not kept, so I consolidated the recurring mechanisms into *The Deployment Chasm* and encoded them into the checks below.

The Melbourne employer is named once, here. Earlier employers and my consulting clients are not named; for proof you can verify without calling anyone, start with the public audit and tested tools below.

## Published audit you can re-run {: #sample-audit }

- **[When "not received" means late](../not-received-but-delivered/).** A forensic triage of 2,708 "not received" claims on delivered orders in a public Brazilian marketplace dataset: 1,542 (57%) were written on or before the recorded delivery day, 73 sat at flagged sellers, and 1,093 had no clear cause in the record. The Python code and its tests are public and re-runnable.

## Built systems

I build my own diagnostic and planning tools so I do not arrive on a client's floor with a blank spreadsheet. None of them is in commercial production at a client yet; what they prove is how I translate operational physics into tested software before touching a live system:

- **Inventory and replenishment engine:** 10,483 passing tests in Python and none failing, run on a clean install on 15 November 2026 (private repository). Its decision cards set the engine's recommendation beside the operator's own play and the status quo, and a stock spreadsheet goes from intake to a change that waits for an HMAC-SHA256-signed approval and can be rolled back.
- **Receiving kit:** open source under the MIT licence, with 1,141 passing tests and none failing, run on a clean install on 14 November 2026.
- **Field kit:** 1,187 passing tests on 20 October 2026. It checks an event log against the five-column contract (case, activity, timestamp, who, where) before any analysis runs, and its integrity guards catch a purchase-order line repeated by a one-to-many join, receipts held in blocked stock that do not balance, and negative stock; each guard is tested against a planted defect.
- **Weightlifting planning application:** a full-stack TypeScript monorepo with about 1,332 unit tests, 31 integration tests on an embedded PostgreSQL database and an adversarial review agent written into the repository. Building it for a coach left me a field postmortem on adoption from the builder's side: even when software leaves the expert full editorial control, putting a number on what they used to judge by eye can make them refuse it.

The rule I build to:

<ol class="flow">
<li><strong>Check the extract before the math.</strong> Run integrity guards on the raw tables: a one-to-many join that repeats a purchase-order line, blocked stock that does not balance, and negative stock. Stock in transit is checked inside the replenishment engine, which runs each calculation twice, with and without what is already on the way, to show which ones would order the same goods twice. <span class="flow-stop">If a number fails, nothing is written to the live system.</span></li>
<li><strong>Stage three plays in draft.</strong> Put the engine’s recommendation, the operator’s own adjustment, and the status quo side by side in a draft stage with their working-capital and service-level trade-offs.</li>
<li><strong>Sign off or override with a reason.</strong> The buyer or supervisor approves, modifies, or rejects the draft card; the decision and its reason are logged before execution.</li>
<li><strong>Keep the way back.</strong> Every approved change carries a rollback path and a 90-day check against the floor baseline.</li>
</ol>

One decision card, as it waits for a signature. Pick a play to see what the sign-off records, then take the lead time away to see what the engine does with a cost it cannot measure.

<section class="card-demo" id="decision-card" aria-label="A sample decision card, in draft">
<input class="card-demo-pick" type="radio" name="card-play" id="card-play-a" checked>
<input class="card-demo-pick" type="radio" name="card-play" id="card-play-b">
<input class="card-demo-pick" type="radio" name="card-play" id="card-play-c">
<input class="card-demo-pick" type="checkbox" id="card-no-lead">
<div class="card-demo-head">
<span class="card-demo-title">Decision card: one purchase order for one stock item</span>
<span class="card-demo-state">Draft: waiting for sign-off</span>
</div>
<p class="card-demo-note"><strong>A synthetic sample of the instrument, not a client’s data.</strong> The stock, sales and order figures are invented; the three plays were measured on them by the engine’s own purchase rule.</p>
<div class="card-demo-step">
<h3>First, the integrity gate</h3>
<p>Two probes held the extract before any arithmetic ran:</p>
<ul class="card-demo-probes">
<li><strong>A one-to-many join.</strong> Joining the open purchase order to its delivery schedule repeated one order line three times, so the order on the way would have counted three times over.</li>
<li><strong>Blocked stock that does not balance.</strong> On one order line, more had been released from blocked stock and returned to the supplier than was ever received into it.</li>
</ul>
<p class="card-demo-pass">Both were fixed at the source and the probes ran clean. Only then were the plays measured.</p>
</div>
<div class="card-demo-step">
<h3>Then, three plays on one yardstick</h3>
<p>USD 30,000 of stock on hand, a supplier lead time of 30 days, a cover target of at most 45 days, and a buyer who wants to order USD 48,000. Margin at risk counts double against capital in the ranking.</p>
<div class="card-demo-plays">
<label class="card-demo-play" for="card-play-a" data-play="a">
<span class="card-demo-name">Play A: engine recommendation</span>
<span class="card-demo-what">Stagger the order in two deliveries: half now, half later.</span>
<span class="card-demo-row"><span class="card-demo-k">Working capital committed</span><span class="card-demo-v">USD 24,000</span></span>
<span class="card-demo-row"><span class="card-demo-k">Days of cover</span><span class="card-demo-v">27</span></span>
<span class="card-demo-row"><span class="card-demo-k">Margin at risk of a stockout</span><span class="card-demo-v"><span class="card-demo-measured">USD 2,219</span><span class="card-demo-unmeasured">not measured</span></span></span>
<span class="card-demo-rank"><span class="card-demo-measured">Ranked first</span><span class="card-demo-unmeasured">Tied with play B</span></span>
</label>
<label class="card-demo-play" for="card-play-b" data-play="b">
<span class="card-demo-name">Play B: operator’s adjustment</span>
<span class="card-demo-what">Buy the full order the buyer asked for, measured the same way.</span>
<span class="card-demo-row"><span class="card-demo-k">Working capital committed</span><span class="card-demo-v">USD 48,000</span></span>
<span class="card-demo-row"><span class="card-demo-k">Days of cover</span><span class="card-demo-v">39</span></span>
<span class="card-demo-row"><span class="card-demo-k">Margin at risk of a stockout</span><span class="card-demo-v"><span class="card-demo-measured">USD 0</span><span class="card-demo-unmeasured">not measured</span></span></span>
<span class="card-demo-rank"><span class="card-demo-measured">Ranked second</span><span class="card-demo-unmeasured">Tied with play A</span></span>
</label>
<label class="card-demo-play" for="card-play-c" data-play="c">
<span class="card-demo-name">Play C: do nothing</span>
<span class="card-demo-what">Order nothing now. Inaction has a cost too, and it is shown.</span>
<span class="card-demo-row"><span class="card-demo-k">Working capital committed</span><span class="card-demo-v">USD 0</span></span>
<span class="card-demo-row"><span class="card-demo-k">Days of cover</span><span class="card-demo-v">15</span></span>
<span class="card-demo-row"><span class="card-demo-k">Margin at risk of a stockout</span><span class="card-demo-v"><span class="card-demo-measured">USD 11,096</span><span class="card-demo-unmeasured">not measured</span></span></span>
<span class="card-demo-rank"><span class="card-demo-measured">Ranked third</span><span class="card-demo-unmeasured">Not ranked: its whole cost is what cannot be measured</span></span>
</label>
</div>
<label class="card-demo-lead" for="card-no-lead"><span class="card-demo-measured">Take the lead time away</span><span class="card-demo-unmeasured">Give the lead time back</span></label>
<p class="card-demo-gap card-demo-unmeasured">Without the lead time, margin at risk cannot be measured, so every play says so instead of printing zero. Capital leaves the ranking too: on its own it would always reward the smallest order for what is not known.</p>
</div>
<div class="card-demo-step">
<h3>Last, the sign-off record</h3>
<p class="card-demo-if" data-play="a"><strong>Picked: play A.</strong> The buyer approves the engine’s play. The record keeps the play, who signed, when, and why.</p>
<p class="card-demo-if" data-play="b"><strong>Picked: play B.</strong> An override, logged with its reason: USD 24,000 more capital buys twelve more days of cover<span class="card-demo-measured"> and clears the margin at risk</span>.</p>
<p class="card-demo-if" data-play="c"><strong>Picked: play C.</strong> Doing nothing is a decision too. It is logged with its reason and its cost: <span class="card-demo-measured">USD 11,096 of margin at risk</span><span class="card-demo-unmeasured">not measured, for want of a lead time</span>.</p>
<ul class="card-demo-record">
<li><strong>Who signs.</strong> The buyer. Above a financial threshold, set on the server and not by whoever signs, the card goes to finance instead.</li>
<li><strong>Before the write.</strong> The approval is signed and expires, and the write is refused if the spreadsheet changed after the plan was made.</li>
<li><strong>The way back.</strong> A backup is taken before the write, and one undo puts the sheet back as it was.</li>
<li><strong>Where it writes.</strong> To a working copy of the spreadsheet, never to the live system. The original stays as it came in, beside a twin workbook that carries the decision.</li>
</ul>
</div>
</section>

The code is on [GitHub](https://github.com/esstipi-debug).

## Writing

- Ten field notes, among them [*The Smith and the Tailor*](../the-smith-and-the-tailor/) and [*Nobody Pays for Being Wrong*](../nobody-pays-for-being-wrong/), and ten short answers, among them [why inventory records do not match the shelf](../why-inventory-records-do-not-match-the-shelf/) and [why people follow the system when it is wrong](../why-people-follow-the-system-when-it-is-wrong/).
- [*The Deployment Chasm*](../the-deployment-chasm/), a manuscript on why enterprise and supply-chain systems fail between the contract and the floor.
