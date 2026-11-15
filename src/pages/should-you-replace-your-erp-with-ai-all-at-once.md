---
type: question
order: 35
slug: should-you-replace-your-erp-with-ai-all-at-once
title: Should you replace your ERP with AI all at once?
description: No. The ERP keeps the books, the new piece works beside it in signed drafts, and an old module retires only after its replacement wins in parallel.
published: 2026-11-15
updated: 2026-11-15
origin: the-smith-and-the-tailor
cite: Fowler, M. 2024. "Strangler Fig." *martinfowler.com*. | https://martinfowler.com/bliki/StranglerFigApplication.html
cite: Microsoft. 2026. "Strangler Fig pattern." *Azure Architecture Center*. | https://learn.microsoft.com/en-us/azure/architecture/patterns/strangler-fig
---
No. The ERP keeps the books, so it cannot be switched off for an experiment. Replace it the way a strangler fig replaces its host: one piece at a time, at a seam you can isolate, with the old system still running until each new piece has earned its place on the floor. An AI layer can help with that, but it cannot do it by itself.

## How it works

The fig starts as a small vine on a tree and grows until the tree is no longer needed. In software, you find a seam where one part of the old system can be split off, build the new part there, move the work to it, and only then retire the old part. The code that lets both run side by side is temporary by design.

An AI layer changes one thing. If it sits beside the ERP and reads its exports, the scans, sales and invoices never pass through it, so it strangles nothing on its own. I work with three rules:

- The ERP keeps the books. The new piece writes drafts to a staging area, and nothing reaches the ledger without a person's signature.
- I pick decisions where the floor knows something the system does not, and judge every proposal against two others: what the operator actually did, and what doing nothing would have cost. If neither ever beats the system over a quarter, I audit the deployer before I trust the system.
- An old module retires only when a system built for that job has run beside it and won. That is a purchase or a build with its own cutover, not a side effect of the AI layer.

This is the tailor's way of working from [*The Smith and the Tailor*](../the-smith-and-the-tailor/): measure, baste, fit, and come back for the second fitting. The smith swaps the whole system in one weekend and is gone before the seams give.

## Evidence

Martin Fowler, who named the pattern, writes that replacing a serious system in one go has gone down in flames most of the time: it takes long, users cannot wait for new features, and much of the old behavior turns out to be unwanted. His alternative is gradual: find seams, replace small components first, and accept a transitional architecture that lets old and new coexist, because the lower risk and earlier value outweigh its cost.

Microsoft's guide to the same pattern puts a facade in front of the old system that intercepts requests and routes them to the old or the new part. It also warns that the pattern might not be suitable when requests to the back end cannot be intercepted. A layer that only reads exports is in that situation, which is why it proposes and does not route.

## What this does not prove

- No client has taken an ERP through this path with me from start to finish. Replacing one module by module takes years, and I have not seen it completed.
- Fowler and Microsoft write about software modernization in general, not about ERPs in warehouses or plants.
- The three rules are my reading of the pattern for an AI layer. They are a method, not a tested result.
