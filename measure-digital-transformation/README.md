# Measure Digital Transformation: companion code

Companion code for the LinkedIn newsletter *Measure Digital Transformation* by Dr. Eddie Lin. Each folder pairs one edition's leadership question with a measurement strategy, the statistics behind it, and runnable Python and R code on a synthetic dataset.

All data in these folders are synthetic, generated to illustrate the methods. They do not come from Meta, any client, or any real organization.

| Edition | Folder | Method |
|---|---|---|
| Adoption Is Not Impact: How to Prove a GenAI Rollout Actually Worked | [A01_adoption-is-not-impact](A01_adoption-is-not-impact) | Difference-in-differences; staggered-adoption (group-time) estimators |
| Who Audits the Agents? Human Oversight as a Measurable Capability | [C01_who-audits-the-agents](C01_who-audits-the-agents) | Chance-corrected agreement (Cohen's kappa, Krippendorff's alpha); golden-set accuracy |

Each folder's README explains how to run it: `python3 data/generate_data.py`, then the R and Python analysis scripts.
