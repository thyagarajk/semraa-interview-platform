# M1: your steps (beginner-friendly)

The M1 voice test ran on the 8 GB laptop, so its results are provisional. Four things finish it:

1. Re-run the test on the RTX 5070 Ti PC. This gives the real go/no-go and settles the LLM size.
2. Record about 10 English and 10 Tamil real answers, so the accuracy numbers come from real speech.
3. Have a Tamil speaker review the AI's Tamil replies and voice.
4. Ask legal to check one licence (GPL-3.0).

Do 1 first. 2 and 3 can happen on the same PC afterwards. 4 is an email you can send at any time.

> **Shortcut:** you can skip typing the commands yourself. Open the Claude desktop app on the GPU PC and tell
> Claude in the project thread "run M1 on this PC". It will run steps 1.4 to 1.9 for you. You still do
> 1.1 to 1.3, because those involve your accounts.

---

## Step 1: re-run on the RTX 5070 Ti PC (about 1 to 2 hours, mostly downloads)

Open **PowerShell** for every command below: Start menu → type `PowerShell` → open it. Do not use "Run as
administrator". Paste each command and press Enter.

### 1.1 Check the graphics driver

```powershell
nvidia-smi
```

You should see **NVIDIA GeForce RTX 5070 Ti** and about **16303MiB** of memory. If the command isn't found, or the
driver version is below 570, install the latest **Game Ready** or **Studio** driver from nvidia.com/drivers
and restart the PC.

Also check that the drive you'll use has **at least 60 GB free**, because the models are large.

### 1.2 Install the tools (one time)

```powershell
winget install --id Git.Git -e
winget install --id astral-sh.uv -e
winget install --id Ollama.Ollama -e
```

Click Yes on any prompt. Then **close PowerShell and open a new one**, so the new tools are found. Check them:

```powershell
git --version
uv --version
ollama --version
```

You don't need to install Python yourself. `uv` downloads Python 3.12 automatically in step 1.5.

### 1.3 Set your Hugging Face token on this PC

The Tamil models need the same token you made on the laptop. You can create a new **Read** token at
https://huggingface.co/settings/tokens. Then run:

```powershell
setx HF_TOKEN "paste-your-token-here"
```

**Close PowerShell and open a new one.** `setx` only affects windows opened after it runs. Never paste the
token into chat, email or a file in the repo.

### 1.4 Get the code

Pick a folder, for example `D:\Semraa`:

```powershell
mkdir D:\Semraa -Force
cd D:\Semraa
git clone https://github.com/thyagarajk/semraa-interview-platform.git
cd semraa-interview-platform
git checkout m1-voice-spike
```

(Once PR #2 is merged, `git checkout main` is enough.)

### 1.5 Install the spike's packages

```powershell
cd workers
uv sync --all-packages --extra models --extra tamil
```

This takes 10 to 20 minutes. It downloads Python 3.12, PyTorch with CUDA, and the speech libraries.

### 1.6 Download the LLMs into Ollama

Ollama starts by itself after install (look for the llama icon near the clock). Then:

```powershell
ollama pull qwen3:8b
ollama pull qwen3.5:9b
ollama pull qwen2.5:7b
ollama pull qwen3:14b
```

That's about 25 GB in total. `ollama list` shows them when they're done.

### 1.7 Run the benchmark

You should still be in the `workers` folder:

```powershell
uv run semraa-spike bench --pipeline-llm qwen3:8b qwen3.5:9b qwen3:14b
```

- The first run also downloads the speech models (Whisper, Kokoro, IndicConformer, Indic Parler-TTS).
- Total time is roughly 30 to 60 minutes. Don't use the PC for heavy work while it runs, so the timings stay fair.
- If a line says `HF_TOKEN` or `403`, step 1.3 didn't take effect. Open a new PowerShell and run the command
  again.

### 1.8 Read the results

The results are written to:

- `workers\spike\results\latest.md`: the tables. Open it in VS Code or Notepad.
- `workers\spike\results\<date-time>.json`: the raw numbers.

The rows that matter most are **Turn latency** for `en` and `ta`. Targets: p50 ≤ 1500 to 2000 ms, p95 ≤ 3000 ms.

### 1.9 Send the results back

```powershell
cd ..
git add workers/spike/results
git commit -m "M1: results from RTX 5070 Ti"
git push
```

The first `git push` opens a GitHub sign-in window. Sign in as **thyagarajk**. Then tell Claude "results pushed",
and Claude updates the report and STATUS.md with the go/no-go and the LLM size.

---

## Step 2: record real answers (about 1 hour)

### 2.1 Who and consent

- Find 2 to 4 adults (18+). A mix of accents is ideal: Tamil-speaking English, plus at least 1 to 2 people
  fluent in Tamil.
- Before recording, read this to each person and get a "yes" (a signed paper or a reply email is best):

> "We are testing an AI interview system. We'll record your voice reading a few short answers. The
> recordings are used only to measure how well the system understands speech. They are not shared publicly or
> used to judge you, and they are deleted within 90 days. You can ask us to delete them at any time. Do you agree?"

- Keep the consent records with you, not in the repo.

### 2.2 Set up Windows Sound Recorder

1. Start menu → **Sound Recorder**.
2. Open **⋯ → Settings → Recording format** and choose **WAV**.
3. Use a headset or a quiet room. Speak at a normal distance from the microphone.

### 2.3 What to read

The texts are in the repo:

- English: `workers\spike\fixtures\en.jsonl`, ids `en01` to `en10`
- Tamil: `workers\spike\fixtures\ta.jsonl`, ids `ta01` to `ta10`

Each line has a `question` and a `text`. The speaker reads the **text** aloud in a natural, interview-like
voice. For each recording:

- Wait **half a second** after pressing record before speaking.
- After the last word, **stay silent for 3 seconds**, then stop. The system needs that silence to decide the
  answer has ended.
- Retake any recording with a stumble.
- If the speaker changes words, edit that line's `text` in the `.jsonl` file so it matches exactly what they said.

### 2.4 Name and place the files

- Rename each recording to its id, for example `en01.wav` or `ta07.wav`.
- **Back up** the original synthetic files first: copy the folder `workers\spike\fixtures\audio` to
  `D:\Semraa-private\synthetic-backup`.
- Copy your recordings into `workers\spike\fixtures\audio\`, replacing the files with the same names. Any sample
  rate is fine; the tool converts it.
- In each `.jsonl` line you replaced, change `"voice"` to a code such as `"real-A"` or `"real-B"`. **Never use a
  person's name.**

### 2.5 Run accuracy only, then protect the recordings

```powershell
cd D:\Semraa\semraa-interview-platform\workers
uv run semraa-spike bench --skip-llm
```

Afterwards:

1. **Move** your real recordings out of the repo to `D:\Semraa-private\recordings` (a private folder that is
   not synced to the cloud).
2. Put the synthetic files back: `git checkout -- spike/fixtures/audio`.
3. Check with `git status` that **no real `.wav` files** are listed. The repo is public, and voices are personal
   data.
4. Push only the results, as in step 1.9. If you edited the `.jsonl` texts, push those too; they contain no
   personal data.
5. Put a calendar reminder to delete `D:\Semraa-private\recordings` 90 days from today.

---

## Step 3: Tamil listener review (about 30 minutes)

Ask a fluent Tamil speaker to sit at the GPU PC with headphones. For each Tamil test answer, run this from
`workers`:

```powershell
uv run semraa-spike run --wav spike/fixtures/audio/ta01.wav --lang ta --play --show-text
```

Change `ta01` to `ta02` and so on up to `ta10`. The command shows what the system heard, shows the AI
interviewer's reply text, and plays the reply in the Tamil voice.

The reviewer fills in this table on paper or in a spreadsheet:

| id | Heard correctly? (yes / mostly / no) | Reply natural Tamil? (1 to 5) | Reply makes sense for the answer? (1 to 5) | Voice clear? (1 to 5) | Garbled or cut off? (yes / no) | Notes |
|---|---|---|---|---|---|---|
| ta01 | | | | | | |
| … | | | | | | |
| ta10 | | | | | | |

The reviewer can also read the replies of every model, without audio, in `workers\spike\results\latest.json`.
Search for `"lang": "ta"` and then `"replies"`. Send the filled table to Claude, which adds the result to the
report.

---

## Step 4: licence check by legal (email, 5 minutes)

Send this to your lawyer or CA:

> Subject: Open-source licence check: GPL-3.0 components in Semraa's voice server
>
> Our AI interview platform's English text-to-speech uses **kokoro-onnx** (MIT licence). It depends on
> **espeak-ng** and **phonemizer**, which are **GPL-3.0**. They run only inside our own server software,
> which we host ourselves. Users reach it over the internet and receive no copy of the software.
>
> Questions:
> 1. Is using GPL-3.0 components this way (hosted service, no distribution) acceptable for a commercial product?
> 2. If we later install the platform on a college's own servers (on-premises), does that count as distribution, and
>    what would we then have to provide?
> 3. Are there obligations we must meet even in the hosted case (notices, attribution)?

If the answer is no, or "only with conditions we don't want", tell Claude. There are permissively licensed
alternatives: Kokoro with its own English pronunciation module, or a pronunciation dictionary. They need a
little more work to read technical words such as "Kubernetes" correctly.

---

## Checklist

- [ ] 1. GPU PC benchmark run and results pushed
- [ ] 2. Real recordings: consent collected, accuracy run done, recordings moved out of the repo, deletion reminder set
- [ ] 3. Tamil review table filled and sent
- [ ] 4. Legal email sent, answer received
