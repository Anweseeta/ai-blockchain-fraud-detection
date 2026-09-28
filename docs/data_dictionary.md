# Data Dictionary — transaction_dataset.csv

Source: `data/raw/transaction_dataset.csv` (9,841 rows × 51 columns, account-level Ethereum behavioral aggregates).
Generated from actual inspection on 2026-09-25. Column order preserved from the file.

Legend — Role: `feature` | `target` | `identifier` | `potentially leaky` | `unusable` (constant/meaning unverifiable).
Decision: KEEP = used in modeling pipeline; REMOVE = excluded with reason below.

| # | Column | Data Type | Description | Role | Decision | Reason |
|---|--------|-----------|-------------|------|----------|--------|
| 0 | `Unnamed: 0` | int64 | Row number written by the tool that exported the CSV (pandas index artifact). | potentially leaky | **REMOVE** | Encodes dataset row order. Pearson r = **0.72 with FLAG** — rows are sorted by label (first 4,920 rows are 100% FLAG=0). Pure leakage, not a blockchain property. |
| 1 | `Index` | int64 | Row-group id from the source scrape (only 4,729 unique values for 9,841 rows). | potentially leaky | **REMOVE** | r = −0.32 with FLAG; fraud concentrates at low Index values (FLAG=1 rate 33% for Index≤1500 vs 0% for Index>4000). Same sort artifact as above. |
| 2 | `Address` | object | Ethereum address, unique account identifier (9,816 unique / 9,841 rows). | identifier | **REMOVE** | Unique per row — a model would memorize it. Also note: 50 rows (25 addresses) appear twice; labels are consistent within each duplicated address, so rows can be kept. Recommend group-aware splitting by Address. |
| 3 | `FLAG` | int64 ∈ {0,1} | Target label: 0 = legitimate, 1 = fraud/suspicious. Per the dataset's own convention (no external doc shipped with the file). | target | **KEEP** | Supervision signal. |
| 4 | `Avg min between sent tnx` | float64 | Average minutes between outgoing transactions. 0 where Sent tnx = 0 (verified: no sent==0 row has a nonzero value). | feature | **KEEP** | Behavioral tempo. Heavy right tail (max 430k min) — log-transform for linear models. |
| 5 | `Avg min between received tnx` | float64 | Average minutes between incoming transactions. 0 where Received Tnx = 0. | feature | **KEEP** | Behavioral tempo. |
| 6 | `Time Diff between first and last (Mins)` | float64 | Activity span of the account in minutes. | feature | **KEEP** | r = −0.27 with FLAG: fraudulent accounts tend to be short-lived (burner behavior). Genuine behavioral signal, not leakage. |
| 7 | `Sent tnx` | int64 | Count of sent transactions (max 10,000 — capped in source). | feature | **KEEP** | Core activity measure. |
| 8 | `Received Tnx` | int64 | Count of received transactions. | feature | **KEEP** | Core activity measure. |
| 9 | `Number of Created Contracts` | int64 | Contracts deployed by the account (max 9,995). | feature | **KEEP** | Contract-creation behavior is scam-relevant. |
| 10 | `Unique Received From Addresses` | int64 | Distinct senders (max 9,999). | feature | **KEEP** | Counterparty diversity. |
| 11 | `Unique Sent To Addresses` | int64 | Distinct recipients (max 9,287). | feature | **KEEP** | Counterparty diversity. |
| 12 | `min value received` | float64 | Smallest received amount (ETH). | feature | **KEEP** | Value profile. |
| 13 | `max value received ` | float64 | Largest received amount (ETH). Trailing space is in the original header. | feature | **KEEP** | Value profile. |
| 14 | `avg val received` | float64 | Mean received amount (ETH). | feature | **KEEP** | Value profile. |
| 15 | `min val sent` | float64 | Smallest sent amount (ETH). | feature | **KEEP** | Value profile. |
| 16 | `max val sent` | float64 | Largest sent amount (ETH). | feature | **KEEP** | Value profile. |
| 17 | `avg val sent` | float64 | Mean sent amount (ETH). | feature | **KEEP** | Value profile. |
| 18 | `min value sent to contract` | float64 | Smallest value sent to a contract (only 3 unique values, ~all zero). | feature | **KEEP** | Very low variance; keep for now, review in ablation. |
| 19 | `max val sent to contract` | float64 | Largest value sent to a contract (4 unique values). | feature | **KEEP** | Very low variance; keep for now. |
| 20 | `avg value sent to contract` | float64 | Mean value sent to a contract (4 unique values). | feature | **KEEP** | Very low variance; keep for now. |
| 21 | `total transactions (including tnx to create contract` | int64 | Total transaction count incl. contract creation (header truncated in the source file). 529 rows are 0. | feature | **KEEP** | Overall activity. |
| 22 | `total Ether sent` | float64 | Lifetime ETH sent. | feature | **KEEP** | Monetary footprint. |
| 23 | `total ether received` | float64 | Lifetime ETH received. | feature | **KEEP** | Monetary footprint. |
| 24 | `total ether sent contracts` | float64 | ETH sent to contracts (4 unique values, ~all zero). | feature | **KEEP** | Very low variance; keep for now. |
| 25 | `total ether balance` | float64 | received − sent style balance; **can be negative** (min −15.6M). | feature | **KEEP** | Negative values are an accounting artifact of the source scrape, not invalid data — do not drop the rows. Keep, document. |
| 26 | ` Total ERC20 tnxs` | float64 | Count of ERC20 token transfers. 829 rows NaN = no ERC20 activity (verified: same 829 rows are NaN across all ERC20 numerics). | feature | **KEEP** | Impute NaN → 0 (semantically "none"). |
| 27 | ` ERC20 total Ether received` | float64 | Token-value received (source units, huge magnitudes). | feature | **KEEP** | Impute 0. |
| 28 | ` ERC20 total ether sent` | float64 | Token-value sent. | feature | **KEEP** | Impute 0. |
| 29 | ` ERC20 total Ether sent contract` | float64 | Token-value sent to contracts (30 unique). | feature | **KEEP** | Impute 0. |
| 30 | ` ERC20 uniq sent addr` | float64 | Distinct token-sending counterparties (108 unique). | feature | **KEEP** | Impute 0. |
| 31 | ` ERC20 uniq rec addr` | float64 | Distinct token-receiving counterparties (148 unique). | feature | **KEEP** | Impute 0. |
| 32 | ` ERC20 uniq sent addr.1` | float64 | Meaning **unverifiable** (`.1` suffix = duplicate header from source export). 8,984 zeros, 1,002 NaN-or-tiny. ~uncorrelated (−0.003) with the similarly named column 30. | unusable | **REMOVE** | Near-zero variance + meaning cannot be verified from the data. Cannot be trusted as a feature. |
| 33 | ` ERC20 uniq rec contract addr` | float64 | Distinct contract addresses receiving tokens (124 unique). | feature | **KEEP** | Impute 0. |
| 34 | ` ERC20 avg time between sent tnx` | float64 | All zeros (2 unique: 0, NaN pattern). | unusable | **REMOVE** | Zero variance — no information. |
| 35 | ` ERC20 avg time between rec tnx` | float64 | All zeros. | unusable | **REMOVE** | Zero variance. |
| 36 | ` ERC20 avg time between rec 2 tnx` | float64 | All zeros. | unusable | **REMOVE** | Zero variance. |
| 37 | ` ERC20 avg time between contract tnx` | float64 | All zeros. | unusable | **REMOVE** | Zero variance. |
| 38 | ` ERC20 min val rec` | float64 | Min token value received. | feature | **KEEP** | Impute 0. |
| 39 | ` ERC20 max val rec` | float64 | Max token value received. | feature | **KEEP** | Impute 0. |
| 40 | ` ERC20 avg val rec` | float64 | Mean token value received. | feature | **KEEP** | Impute 0. |
| 41 | ` ERC20 min val sent` | float64 | Min token value sent. | feature | **KEEP** | Impute 0. |
| 42 | ` ERC20 max val sent` | float64 | Max token value sent. | feature | **KEEP** | Impute 0. |
| 43 | ` ERC20 avg val sent` | float64 | Mean token value sent. | feature | **KEEP** | Impute 0. |
| 44 | ` ERC20 min val sent contract` | float64 | All zeros. | unusable | **REMOVE** | Zero variance. |
| 45 | ` ERC20 max val sent contract` | float64 | All zeros. | unusable | **REMOVE** | Zero variance. |
| 46 | ` ERC20 avg val sent contract` | float64 | All zeros. | unusable | **REMOVE** | Zero variance. |
| 47 | ` ERC20 uniq sent token name` | float64 | Count of distinct tokens sent (71 unique). | feature | **KEEP** | Impute 0. |
| 48 | ` ERC20 uniq rec token name` | float64 | Count of distinct tokens received (122 unique). | feature | **KEEP** | Impute 0. |
| 49 | ` ERC20 most sent token type` | object | Most-used sent token name. 304 unique + NaN (2,697) + `'0'` (4,399, = none/unknown) + `' '` (1,191). NaN is 38% in fraud vs 24% in legit — the missingness itself is informative. | feature | **KEEP** | Clean `'0'`/`' '`/NaN → `'none'`; then top-k one-hot or target encoding (fit on train only). High cardinality — treat carefully. |
| 50 | ` ERC20_most_rec_token_type` | object | Most-used received token name. 466 unique + NaN (871) + `'0'` (4,399). Same encoding semantics. | feature | **KEEP** | Same treatment as column 49. |

**Resulting feature set: 39 features** — 37 numeric + 2 categorical (token-type names).

### Removed (11)
- Leakage/identifiers: `Unnamed: 0`, `Index`, `Address`
- Zero-variance: ` ERC20 avg time between sent tnx`, ` ERC20 avg time between rec tnx`, ` ERC20 avg time between rec 2 tnx`, ` ERC20 avg time between contract tnx`, ` ERC20 min val sent contract`, ` ERC20 max val sent contract`, ` ERC20 avg val sent contract`
- Unverifiable: ` ERC20 uniq sent addr.1`
