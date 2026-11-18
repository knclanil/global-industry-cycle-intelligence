# Global Factor category

Five user-designated Global Factor sources are registered: 271538, 275382, 239499, 239605, 271540. The collector reads each actual fund title from the first CSV cell, retains the title, and derives the visible factor-type label from that title. Unknown factor types are displayed as Other / Unclassified, not guessed.

These five are distinct from USA Factor, USA Sector, and Global Sector. Their holdings are included in verified snapshots, coverage reporting and fund drilldowns. A separate Global Factor leadership table is generated using 55% cross-fund breadth and 45% relative ETF weight; this provisional analytical score is NOT the USA 45/40/15 score, which remains unchanged. No holdings are invented. The next GitHub Actions run must retrieve and verify the new sources before any Global Factor ranking data appears.
