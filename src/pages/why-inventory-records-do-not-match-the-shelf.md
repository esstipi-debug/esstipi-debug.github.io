---
type: question
order: 80
slug: why-inventory-records-do-not-match-the-shelf
title: Why don't inventory records match the shelf, and what does that do to a model?
description: In one retailer's audit, 65% of nearly 370,000 records did not match the shelf. A model trained on them is wrong exactly where the record is.
published: 2026-11-09
updated: 2026-11-09
origin: nobody-pays-for-being-wrong
cite: DeHoratius, N., and A. Raman. 2008. "Inventory record inaccuracy: An empirical analysis." *Management Science* 54(4): 627–641. | https://doi.org/10.1287/mnsc.1070.0789
---
Because the record changes only when someone types, and the shelf changes all day. The gap is larger than most teams assume: in one retailer's audit, 65% of nearly 370,000 inventory records did not match the shelf. A model trained on those records can be careful, elegant and wrong in exactly the places where the record is wrong. Check it against a blind count before you trust it.

## How it works

An analytics team, or a model, never sees the shelf. It sees what the shelf was recorded as. When the record is wrong, the error is paid on the floor and booked in finance, so the people who draw the floor from the record rarely find out where.

Medieval illustrators drew lions they had never seen, from descriptions and earlier drawings. A model built from exports is the same kind of lion. The cheapest correction is a physical count by someone who cannot see the system's number, and a note next to every model saying which numbers were counted and which were typed. Most models carry no such note, and nobody asks for one.

## Evidence

Nicole DeHoratius and Ananth Raman examined nearly 370,000 inventory records from 37 stores of one retailer and found 65% to be inaccurate. The error had structure: auditing practices reduced it, while a more complex store environment and the distribution structure made it worse.

## What this does not prove

- One retailer and 37 stores. The share will differ elsewhere, and a store is not a warehouse.
- The lion is my image. It does not measure how often models fail.
- The blind count is a practice, not a tested threshold.
