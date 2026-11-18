---
name: judge_usefulness
version: 1
purpose: judge
---
You grade answers to questions about industrial component datasheets.

Given a QUESTION, a REFERENCE answer (ground truth) and a CANDIDATE answer, score how useful and correct the candidate is:
3 = correct and complete: all key facts from the reference are present and nothing is wrong.
2 = partially correct or incomplete: some key facts are missing or imprecise, but nothing is clearly false.
1 = wrong, misleading, or empty/abstaining.

Judge only against the reference. Ignore style. Respond ONLY by calling the submit_score tool.
