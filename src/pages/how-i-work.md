---
type: page
order: 20
slug: how-i-work
title: How I diagnose an operation
kicker: How I work
description: How I diagnose an operation: walk the floor first, ask what happened, put the record and the floor on one timeline, and write the working down.
subject: What we're seeing
published: 2026-11-09
updated: 2026-11-16
---
**I walk it first.** Dust on a rack is stock that has not moved. A sheet taped beside the terminal is a gap the software left. I include the 02:30 shift, when supervision thins out and the real process shows.

**I ask what happened, not what people think.** "Last time this order went wrong, what did you do?" Past behaviour, not opinions.

**I put the record and the floor on one timeline.** Five columns: case, activity, timestamp, who, where.

**I write the working down.** I usually see the shape of the problem early. The SQL, the process map and the one-page spec are there so finance, the floor and engineering can check it instead of trusting me. For an engineering team that includes the data contract: which fields the system will read, who writes them, and how far each one can be trusted, with a tolerance for each field, the join rules the extract must keep, edge cases they can reproduce, and the condition that triggers the way back. They build on a specification tested against the floor, not on a wish.

**Mise en place before go-live.** No kitchen opens for service before everything is weighed, portioned and checked. No system should go live before its data is staged, checked and signed, with a way back.

**A screen has to work on shift, not in a meeting room.** One that works at a desk can fail with gloves, a scanner and a queue at 02:30, and then the crew goes back to paper. Routine steps get no extra clicks; an override gets one deliberate step: the reason is written before saving, for a reviewer whose view the operator does not know. I have not run a measured usability study. What I have is the floor: I trained twenty-three operators on RF scanning and stayed until the shortcuts died.

No favourite tool, no favourite method. I measure before I cut.
