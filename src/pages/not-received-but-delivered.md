---
type: question
order: 90
slug: not-received-but-delivered
title: A customer says “not received” and the system says “delivered”: which record is wrong?
description: Often neither. In a public marketplace dataset, 57% of “not received” reviews on delivered orders were written on or before the delivery day.
published: 2026-11-09
updated: 2026-11-14
origin_label: the demo Which Record Lies? (code, tests and method)
origin_url: https://github.com/esstipi-debug/esstipi-debug/tree/main/demos/which-record-lies
cite: Olist. *Brazilian E-Commerce Public Dataset by Olist*. Kaggle. Licence CC BY-NC-SA 4.0. | https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
cite: Stipicich, M. 2026. *Which Record Lies?* Triage code, tests and results on the Olist dataset. | https://github.com/esstipi-debug/esstipi-debug/tree/main/demos/which-record-lies
---
Often neither, and the first check is the date. In a public marketplace dataset, 57% of "not received" reviews on orders marked delivered were written on or before the recorded delivery day: late orders, not suspect customers. Put the claim and the delivery record on one timeline before judging anyone.

## How it works

A rule that flags "delivered plus not received" treats every such claim as a conflict between the customer and the record. Two questions come first. When did the customer write, relative to the recorded delivery? A claim written before the delivery was recorded describes a late order, not a conflict. And does what is left concentrate at one origin more than chance allows? Only then is it worth looking at a seller, a carrier or a warehouse.

## Evidence

I ran this triage on the Brazilian E-Commerce Public Dataset by Olist, 2016 to 2018. Of 95,824 delivered orders with a review, 2,708 had a review saying the order had not arrived. Of those, 1,542 (56.9%) were written on or before the recorded delivery day.

The 1,166 left are a conflict between records, but a crude one. In a hand check of 40 of those messages, 22 said the order never arrived; the other 18 were partial deliveries, wrong items, invoices and other matters, and one late delivery. Sellers explain little: 8 of 413 sellers with at least 50 orders sat above a 99% chance threshold, against at most about 4 expected by chance, and together they held 73 of the 1,166 conflicts.

## What this does not prove

- The text filter is crude. It cannot tell "nothing arrived" from a partial delivery or a wrong item, so the conflict count is an upper bound.
- Dates are compared by day: a claim written on the delivery day counts as late.
- One marketplace, one period, and no carrier, route or warehouse data. Nothing here says anything about another company.
- A flagged seller is not a guilty seller.
