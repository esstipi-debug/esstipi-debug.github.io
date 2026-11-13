---
type: landing
order: 40
slug: for-technology-vendors
title: For teams that deploy AI, robots or a WMS into physical operations
kicker: Technology vendors
group: buyer
door: I sell technology into these floors
door_text: Applied AI, warehouse robotics, WMS and ERP teams.
description: For applied-AI, robotics and WMS teams: read the customer's record before go-live, stage the cutover with a way back, and check adoption at 90 days.
subject: Deployment into physical operations
published: 2026-11-09
updated: 2026-11-09
---
A pilot can pass every acceptance test and still be bypassed on the night shift. Not out of malice: when the dock is full, the old way is faster.

Passing once is not holding. In τ-bench, a public test of AI agents handling retail customer requests, even the strongest agents tested in 2024 solved fewer than half of the tasks, and the chance of getting the same task right eight times in a row was under a quarter. And the model is the small part: a mature machine-learning system might end up at most 5% model code and at least 95% glue, the code that connects it to the operation.

Sources: Yao and others, [τ-bench](https://arxiv.org/abs/2406.12045), 2024. Sculley and others, [Hidden Technical Debt in Machine Learning Systems](https://papers.nips.cc/paper_files/paper/2015/file/86df7dcfd896fcaf2674f757a2463eba-Paper.pdf), 2015.
{: .src }

## What I check first

Your customer's record, read the way your system will read it: how much of it is true. What the crew is paid for, and whether your system measures the same thing. Where your screen is slower than the workaround.

## Where I have stood

I have lived the record your agent will read, and the people who write it: thirteen years in planning, inventory and distribution, and a 50,000-SKU warehouse-system changeover where I stayed on the floor until the shortcuts died ([the record](../proof/#track-record)). I learned to code in C, so I read a warehouse the way a C programmer reads memory: every location is an address, a stockout is a pointer to an empty one, and excess stock is memory nobody freed. Today I build with AI coding agents, keeping the math and the rollback in my hands.

## What I don't claim

I have not deployed AI agents for a vendor, and none of the systems I have built runs a client's operation yet.

## How we would start {: #how-we-would-start }

Five steps, from the first audit to the handback.

<div class="steps" markdown="1">

1. **Discover on the floor.** Before go-live, at one customer site, I walk every shift beside the crew, so engineering does not build on a flow that exists only on paper. *Out: a map of the decisions, checked on the floor, and the first use cases.*
2. **Tune.** A baseline from your customer's own data, and a blind count of a sample of SKUs to measure how much of the recorded stock is really there, repeated every cycle. *Out: the baseline, and a map of where the record holds.*
3. **Orchestrate.** Through go-live: one steering meeting on one number, use cases in sequence starting where the record holds, floor instruction in the crew's own terms and a staged go-live with a way back. *Out: live use cases, each with an owner and measured adoption.*
4. **Value case.** After go-live, the impact against the baseline, and the 90-day check: who still uses it, who went around it, and why. *Out: the value story for the renewal and the next use cases.*
5. **Let go.** Handback with your engineers to customer success: success criteria met, value documented, and a map of the next use cases, sites and teams. *Out: a clean handback.*

</div>

At every step your engineers get it in writing: a one-page spec, the data contract (which fields the system will read, who writes them, and how far each one can be trusted) and success criteria signed before kickoff. [The one-page plan](../files/client-onboarding-plan.pdf) (PDF) puts it on a page.
