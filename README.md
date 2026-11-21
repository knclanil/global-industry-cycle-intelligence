# Knowledge Graph company membership count columns

Replace `regional_rotation_graph.py` in the root of your GitHub Desktop repository with the file in this ZIP. Do not replace `app.py` or any data caches. Commit and push with GitHub Desktop.

In the **All verified company memberships** table, the existing one-row-per-company presentation now includes:

`Company | Ticker | Quadrant | # Quadrant | Sector | # Sector | Factor | # Factor | Mapping | Weight | Avg Weight`

Counts are the number of **distinct displayed** quadrant classifications, sector labels, and normalized factor families for each company, calculated only from the membership records in the table's currently selected mode and filters. Multiple underlying indexes in the same factor family count once; duplicated source records do not inflate counts. No extra graph filtering or cache rebuild is introduced. If some memberships are excluded by the chosen table mode, counts reflect the visible membership evidence, not necessarily all the company's memberships.

`# Quadrant` counts distinct labels in the Quadrant cell, `# Sector` counts distinct sector labels, and `# Factor` counts normalized factor families. Blank/missing values do not contribute to counts. The underlying detailed membership evidence remains accessible in the existing expander.

Validation: Python syntax and three targeted aggregation tests passed. Live Streamlit deployment not tested.
