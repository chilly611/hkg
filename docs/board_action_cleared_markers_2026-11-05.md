# Board actions the board marks cleared

Ruled 2026-11-05. Applies to `state_board_action` receipts (`migrations/2026-11-05_board_action_receipts.sql`).

## The rule

1. **The receipt stays verbatim.** A board action the file lists on a license tied to the NPI by license number reads `action_on_record`, in the board's own words, whether or not the board has since cleared it. The board lists it as a board action, so the receipt says so.
2. **An action is marked cleared by the board** only when its own text carries the board's cleared marker, as listed below for its state. The markers are matched on the action as stored in `claim.actions[]`, after trimming and upper-casing. Nothing else counts: no inference from dates, from "SEE PREVIOUS ORDER" alone, or from words that only resemble clearance.
3. **A receipt is marked cleared** (`marked_cleared_by_board`) when every action it lists is marked cleared. If any action is not, the receipt stays adverse.
4. **Roster.** A receipt marked cleared goes to the **unresolved** queue with the chip "board action, marked cleared by board". It does not go to adverse. Every other `action_on_record` stays adverse, with the chip "board action on record".
5. **Provider summary.** When the board marks the action cleared, the board action sentence ends "the board marks it cleared" ("them all cleared" when several are listed). When only the latest action is marked, it ends "the board marks that one cleared".
6. **A state with no markers listed here never clears.** Florida's "Obligation(s) Satisfied", "Probation Satisfied" and "Restriction Satisfied" are not ruled on and stay adverse. California's file lists no actions at all.

The flag is computed when the API answers (`CLEARED_MARKERS` and `markCleared()` in `supabase/functions/freshroot/index.ts`) and is never stored. It appears on roster checks, on `/v1/providers/{npi}/claims` and on `/v1/deltas`. Each listed action also carries `cleared_by_board_marker`: the matched text, or null.

## Texas: the exact markers

Source: Texas Medical Board licensure file, Texas Open Data tm3v-pfq9. Counts are from run `d8d59cc2` (file dated 2026-11-04), whose 873 matched action rows were read on 2026-11-05.

| Marker | Where in the file | Match | Rows |
|---|---|---|---:|
| `STATUS CLEARED` | Current Board Action Description (`claim.actions[].description`, classification `Current Board Action`) | the description opens with it, dated or not: `STATUS CLEARED 04/19/2011`, `STATUS CLEARED ON 03/31/2014`, `STATUS CLEARED`, and so on | 258 |
| `STATUS HAS BEEN CLEARED` | Current Board Action Description | the description opens with it | 3 |
| `ON <MONTH> <D>, <YYYY>, STATUS CLEARED` | Current Board Action Description | the description opens with it | 2 |
| `LICENSURE BOARD ORDER CLEARED` | License Status (`claim.actions[].kind`, classification `License Status`) | the whole value | 7 |

The pattern for the description is `^(ON [A-Z]+ \d{1,2}, \d{4},\s+)?STATUS (HAS BEEN )?CLEARED\b`. Of the 263 description matches, the Disciplinary Status reads `SEE PREVIOUS ORDER` on 172 and is blank or NONE (stored as "Board action") on 91.

### Read and deliberately not counted

These stay adverse until a person rules on them:

- `SEE PREVIOUS ORDER` with any other description: 159 rows in that run, such as "LICENSE CANCELLATION CONFIRMED". The pointer is not the marker.
- Descriptions about terminating an order: "ORDER ENTERED GRANTING TERMINATION OF PREVIOUS ORDER", "ORDER TERMINATED DUE TO COMPLETION OF REQUIREMENTS", and "LICENSE FREE AND CLEAR OF ANY PREVIOUS RESTRICTIONS" when it does not follow an opening `STATUS CLEARED`.
- `COMPLAINT DISMISSED`, and `ORDER TERMINATED BECAUSE LICENSE IS NO LONGER ACTIVE`.
- A description that mentions "clear" anywhere other than the opening marker.

To add a marker: read it in the file, add it to this table with its count and to `CLEARED_MARKERS`, in one change.
