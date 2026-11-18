"""Competitor identification prompt logic.

NOTE ON DATA SOURCES: the LLM does not have live web access here, so all
competitor information is generated from the LLM's background knowledge of the
brand's industry. The schema therefore marks every result as
`competitor_data_source: "ai_generated_suggestion"` so downstream users know
competitor details must be verified — per the task requirements.
"""
COMPETITOR_INSTRUCTIONS = """
## Competitor guidance (Section 1)
- Identify 3-5 REAL, well-known competitors in the same market/industry as the
  submitted brand. Use your knowledge of the industry; if you cannot name real
  competitors with confidence, generate plausible competitor profiles and rely
  on the "ai_generated_suggestion" label that the response schema applies.
- For each competitor give: name, main service, target market, one key
  strength, one weakness/gap.
- Compare honestly: list competitor strengths AND weaknesses, the submitted
  brand's competitive advantages, and concrete positioning opportunities.
"""
