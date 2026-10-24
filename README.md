# Mind the Gap

**Built in SF. Fixed in London.**

Big AI models are trained in San Francisco. Ask one to split up a messy London address and it gets the house style wrong most of the time: "Mare Street" instead of "Mare St", "2b" instead of "Flat 2B", "Hackney, London" as the area. Every UK company that uses these models ends up fixing the same mistakes by hand.

Mind the Gap turns those fixes into a London model. The app sends its calls through [Mubit](https://mubit.ai) with one base URL change. The London ops team rates replies in the Mubit console (Good, or Bad with what to fix). Once a task has enough kept examples, Mubit trains a small open model on it automatically.

Built at Night Shift, the Mubit hackathon, Canary Wharf, October 2026.

## Results so far

40 fresh London addresses that were never used for training. 12 of them are on streets the London model has never seen.

| Model | Fully right | Every field | New streets | Median reply |
|---|---|---|---|---|
| GPT-4.1 mini (SF) | 30% | 79% | 33% | 960 ms |
| GPT-6 Sol (SF frontier) | 25% | 75% | 42% | 1,431 ms |
| **London model v1** (Qwen3 4B + Mubit adapter) | **75%** | **94%** | **58%** | **792 ms** |
| GPT-4.1 mini + written house rules | 100% | 100% | 100% | 794 ms |
| GPT-6 Sol + written house rules | 100% | 100% | 100% | 1,326 ms |

With only the short instructions the app really uses, a 4 billion parameter model trained on London corrections gets three times as many addresses fully right as the SF frontier model. Across 260 training calls, GPT-4.1 mini got about 22% fully right.

The fairness check matters too: once the house rules are written into the prompt, both SF models get every address right. So corrections are how you capture rules nobody has written down, and when you can write them down, the big model gets them right but you rent it on every call.

## How the London models were made

**v1, learned from corrections.** 260 calls through Mubit with the short instructions, and about 240 of the replies rated in the console: 53 Good, the rest Bad with a comment saying exactly what to fix. Mubit kept 43 examples, trained a Qwen3 4B adapter, scored it 100% on its own held-out check and put it on a silent test. Its main remaining miss: when the input says "road", it writes "Road" instead of "Rd".

**v2, taught by GPT.** Sending more "road" addresses with the short instructions got 0 of 120 right, so there was nothing Good to learn the fix from. Instead, GPT-4.1 mini with the written rules answered 140 training addresses (127 right). We rated those in the console and Mubit trains a small model on them: the big model teaches, you own the student. Scored on a second fresh test set (`testset2.json`), results coming.

## What we learned about Mubit

- Tasks are grouped by instructions and by model: the same prompt on GPT-4.1 mini and GPT-6 Sol became two tasks with two adapters.
- Mubit's own rater keeps replies automatically, up to 200 ratings a day per project (`adapters.rate.max_per_day`). After that, new calls wait for the next day.
- An adapter retrains once a task has at least 25 new kept rows, and at least half as many as it was last trained on.
- Ratings can only be sent from the console: project keys are either Inference or Read-only. A rating API for ops tools would let apps like this one send their team's fixes straight in.
- Because Mubit keeps good replies on its own, test addresses must never go through the API before the model you're testing has trained. We score adapters in the console's Try models page, which doesn't store or train on anything.

## Run it

You need Python 3.10+ and a Mubit key for this project.

```powershell
git clone https://github.com/ekjots1ngh/mind-the-gap
cd mind-the-gap
pip install openai
$env:MUBIT_API_KEY="your mubit key"    # or copy .env.example to .env and fill it in
python eval_sf.py                      # scores the SF models on the test set
python app.py                          # demo app at http://localhost:8000
```

## What's in here

| File | What it does |
|---|---|
| `app.py`, `static/index.html` | The demo app: ask the SF model about an address, see each field as a station that ticks green or red, copy the correction for Mubit, see the London model's answer, the map and the scoreboard |
| `geo.py` | Finds the postcode on a map (postcodes.io, with offline fallbacks) and the nearest tube station |
| `static/vendor`, `static/data`, `static/fonts` | MapLibre GL JS and GSAP (bundled so the demo works on venue wifi), London station and line data, fonts |
| `house_style.py` | The gap detector. Checks any parsed address against London house style, no right answer needed |
| `grader.py` | Scores a reply against the true answer, field by field |
| `testset.json`, `testset2.json`, `make_testset.py` | The two fresh test sets of 40 addresses (seeds 2026 and 2027) |
| `eval_sf.py` | Runs a test set through the SF models via Mubit (`--rules` adds the written house rules, `--set testset2.json` picks the set) and saves `results/` |
| `send_batch.py` | Sends training traffic (`--v2` writes street names out in full, `--rules` sends teacher traffic with the written rules) |
| `results/` | Scored answers for each model |

Never commit your Mubit key. `.env` is in `.gitignore`.

## Credits

Not affiliated with Transport for London. Map tiles from OpenFreeMap and OpenMapTiles, © OpenStreetMap contributors. Postcode lookups by postcodes.io: contains OS data © Crown copyright and database right, Royal Mail data © Royal Mail copyright and database right, and National Statistics data © Crown copyright and database right (Office for National Statistics, Open Government Licence v3.0). Station and line data © OpenStreetMap contributors (ODbL), prepared by Oliver O'Brien. Maps drawn with MapLibre GL JS (BSD-3-Clause), animation by GSAP, fonts Doto, IBM Plex Mono and Josefin Sans (SIL Open Font License).
