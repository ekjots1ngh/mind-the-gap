# Mind the Gap

**Built in SF. Fixed in London.**

General-purpose models don't know your house style. Ask GPT to split a messy London address into fields and it writes "Mare Street" instead of "Mare St", "2b" instead of "Flat 2B" and "Hackney, London" as the area. Every UK company that uses these models ends up fixing the same mistakes by hand.

Mind the Gap sends those calls through [Mubit](https://mubit.ai) with one base URL change, rates the replies in the Mubit console, and lets Mubit train small Qwen3 4B models on the replies rated Good.

We played the London ops team. A script compared every reply with the known right answer and clicked Good, or Bad with the fix as the comment, in the Mubit console. The addresses are synthetic, built from 15 real London streets, and the house style is ours.

Built at Night Shift, the Mubit hackathon, Canary Wharf, October 2026.

## Results

Each test set is 40 fresh addresses that were never used to train the model scored on it.

**Test set 1** (12 addresses on 5 streets that v1 never saw in training)

| Model | Prompt | Fully right | Every field | Unseen streets | Median reply |
|---|---|---|---|---|---|
| GPT-4.1 mini (SF) | short | 30% | 79% | 33% | 960 ms |
| GPT-6 Sol (SF frontier) | short | 25% | 75% | 42% | 1,431 ms |
| **London model v1** (Qwen3 4B + Mubit adapter) | short | **75%** | **94%** | 58% | 792 ms* |
| GPT-4.1 mini | + written house rules | 100% | 100% | 100% | 794 ms |
| GPT-6 Sol | + written house rules | 100% | 100% | 100% | 1,326 ms |

**Test set 2** (never sent through Mubit before the London model was scored on it)

| Model | Prompt | Fully right | Every field | Median reply |
|---|---|---|---|---|
| GPT-4.1 mini (SF) | short | 12% | 70% | 904 ms |
| GPT-6 Sol (SF frontier) | short | 15% | 72% | 1,572 ms |
| GPT-4.1 mini | + written house rules | 92% | 98% | 797 ms |
| GPT-6 Sol | + written house rules | 100% | 100% | 1,390 ms |
| **London model, taught by GPT** (Qwen3 4B + Mubit adapter) | + written house rules | **100%** | **100%** | 603 ms* |

\* London models were timed in Mubit's Try models page, SF models through the API, so the times aren't like for like.

With the short instructions the app really uses, Mubit's 4B student gets 30 of 40 addresses fully right. GPT-4.1 mini, the model whose Good answers it learned from, gets 12, and GPT-6 Sol gets 10. The student beats its teacher because ratings decide which of the teacher's answers it learns from.

The fairness check matters too. Once the house rules are written into the prompt, both SF models get every address in test set 1 right. So we did what the "own your intelligence layer" track asks: GPT with the rules taught a 4B model. Mubit trained it on 28 of GPT-4.1 mini's answers, and it gets all 40 addresses in test set 2 right, including all 18 that write the street type out in full, which v1 never learned. With the same rules, GPT-4.1 mini itself got 37 of 40 on that set: it split N1 0NY as "N10 NY", read "2b brick lane" as Flat 2B with no house number, and left "Flat 2b" in lower case.

## How the London models were made

**v1, learned from rated answers.** 260 calls through Mubit with GPT-4.1 mini and the short instructions. About 240 replies were rated: 53 Good, the rest Bad with a comment saying what to fix. Mubit only trains on rows rated Good. It kept 43, trained a Qwen3 4B adapter, passed it on its own check (agreement with GPT on 12 held-out rows) and put it on a silent test.

v1's 10 misses on test set 1: 8 are street types written out in full ("Road" for "Rd", "Avenue", "Lane"), one put the house number into the flat label, and one changed the postcode SE22 8HN into SE2 2HN. The gap detector now refuses any postcode that isn't the one in the address.

Ratings couldn't fix "Road". GPT with the short instructions got 0 of 120 such addresses right, so there was never a Good row to keep, and a Bad rating's comment doesn't become training data.

**Taught by GPT.** Calls with the written rules are a separate Mubit task (Mubit groups calls by instructions and by model). Mubit's log shows its adapter was built from the first 40 calls that carried the rules, which were our fairness run on test set 1: the rater kept all 40, Mubit trained on 28 and checked on 12. Its own check gave 66.7% agreement, yet the adapter got all 40 addresses in test set 2 right on our field-by-field grading, so that check and our grader measure different things. We scored it in the Try models page, which doesn't store or train on anything. The 140 teacher addresses we sent afterwards are waiting on the rater's daily cap and the task's 24 hour refresh, so there is no v2 yet.

## What this does not show

- That ratings alone can teach a rule the provider never follows. v1 learned only from GPT's right answers.
- That the taught model is better than its teacher. 40 against 37 out of 40 is too few to call; what it shows is that the 4B student keeps up.
- Generalisation to new streets. On the unseen streets v1 got 7 of 12 against GPT-6 Sol's 5, which is too few to call. The taught model saw all 15 streets in training.
- Cost. We haven't measured it.
- Latency like for like. London models were timed in the playground, SF models through the API.
- Real-world data. The addresses are synthetic and the house style is ours.
- That the long prompt can be retired. The taught model still reads the written rules: it replaces the model, not the prompt.
- Correctness from Mubit's own checks. Those measure agreement with GPT on 12 held-out rows.
- Clean scores for later versions. Test set 1 trained the taught model, and test set 2 goes through the API for the SF baselines, so any new version needs a fresh test set.

## What we'd ask Mubit for

- **Let a rating carry the corrected answer, and train on it.** About 240 ratings bought 43 training rows, and a rule the provider never gets right by chance can't be learned at all. That's our "Road" result.
- **A ratings API.** Project keys are Inference or Read-only, so ratings can only come from the console. We drove the console with browser automation to rate at scale. An endpoint that takes the `x-middleware-request-id` the app already captures would let any ops tool send its team's fixes straight in.
- **A no-train header for eval traffic,** so test sets can go through the API without becoming training rows.
- **Let one task's rows train another task's adapter,** so a teacher on the long prompt can train a student that serves the short one.
- **Don't split tasks when only the model changes, and don't let the rater's daily cap hold back rows a person already rated.**

## What we learned about Mubit

- Tasks are grouped by instructions and by model: the same prompt on GPT-4.1 mini and GPT-6 Sol became two tasks with two adapters.
- Mubit's rater reads up to 200 new calls a day per project (`adapters.rate.max_per_day`). After that, new calls wait.
- An adapter refreshes at most every 24 hours, once its task has 25 new rows rated up and at least half as many as it was last trained on.
- Adapters can't be called from the API yet: they serve through the silent test, or 50 calls a day in the Try models page.
- Because Mubit keeps good replies on its own, test addresses must never go through the API before the model being tested has trained.

## Run it

You need Python 3.10+ and a Mubit key for this project.

```powershell
git clone https://github.com/ekjots1ngh/mind-the-gap
cd mind-the-gap
pip install openai
$env:MUBIT_API_KEY="your mubit key"    # or copy .env.example to .env and fill it in
python eval_sf.py                      # scores the SF models on test set 1
python app.py                          # demo app at http://localhost:8000
python -m unittest discover -s tests   # 15 tests, no key needed
```

If the venue wifi drops, the app replays GPT's recorded answer for test addresses and says so on screen.

## What's in here

| File | What it does |
|---|---|
| `app.py`, `static/index.html` | The demo app: ask the SF model about an address, see each field as a station that ticks green or red, copy the note for Mubit's rating, see the London model's recorded answer, the map and the scoreboard |
| `house_style.py` | The gap detector. Checks any parsed address against London house style, no right answer needed, and guards the postcode |
| `grader.py` | Scores a reply against the true answer, field by field |
| `geo.py` | Finds the postcode on a map (postcodes.io, with offline fallbacks) and the nearest station |
| `testset.json`, `testset2.json`, `make_testset.py` | The two test sets of 40 addresses (seeds 2026 and 2027) |
| `eval_sf.py` | Runs a test set through the SF models via Mubit (`--rules` adds the written house rules, `--set testset2.json` picks the set) and saves `results/` |
| `send_batch.py` | Sends training traffic (`--v2` writes street names out in full, `--rules` sends teacher traffic with the written rules) |
| `results/` | Scored answers for each model, test set 2 in `results/testset2/` |
| `tests/` | Tests for the grader, the gap detector and the map lookup |
| `static/vendor`, `static/data`, `static/fonts` | MapLibre GL JS and GSAP (bundled so the demo works on venue wifi), London station and line data, fonts |

Never commit your Mubit key. `.env` is in `.gitignore`.

## Credits

Not affiliated with Transport for London. Map tiles from OpenFreeMap and OpenMapTiles, © OpenStreetMap contributors. Postcode lookups by postcodes.io: contains OS data © Crown copyright and database right, Royal Mail data © Royal Mail copyright and database right, and National Statistics data © Crown copyright and database right (Office for National Statistics, Open Government Licence v3.0). Station and line data © OpenStreetMap contributors (ODbL), prepared by Oliver O'Brien. Maps drawn with MapLibre GL JS (BSD-3-Clause), animation by GSAP, fonts Doto, IBM Plex Mono and Josefin Sans (SIL Open Font License).
