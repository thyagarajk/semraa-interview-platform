<#
.SYNOPSIS
    Live M1 voice-interviewer test on the microphone, in English or Tamil.

.DESCRIPTION
    Runs `semraa-spike run --mic`: speak an answer, pause, and the AI interviewer replies out loud.
    Only latency timings are printed. Transcripts and replies are never shown or written to disk
    (no --show-text, no transcript file).

    Wear headphones: with laptop speakers the microphone hears the AI and can take its voice as your answer.
    Windows plays through whatever the default output device is, so plug the headphones in before starting.

    Stop with Ctrl+C.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File Z:\Semraa\semraa-interview-platform\workers\spike\scripts\live-test.ps1 -Lang en

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File Z:\Semraa\semraa-interview-platform\workers\spike\scripts\live-test.ps1 -Lang ta
#>
param(
    [ValidateSet('en', 'ta')]
    [string]$Lang = 'en',

    # Silence that ends your answer. Raise it (up to 2500) if it cuts you off mid-thought.
    [ValidateRange(1500, 2500)]
    [int]$SilenceMs = 1800,

    [string]$Llm = 'qwen3:8b',

    # The interviewer's opening question (the AI itself replies in the chosen language).
    [string]$Question = 'Tell me about a project you built.'
)

$ErrorActionPreference = 'Stop'
$workers = Resolve-Path (Join-Path $PSScriptRoot '..\..')
Set-Location $workers

# Quieter model loading; nothing here prints what was said.
$env:PYTHONUNBUFFERED = '1'
$env:TRANSFORMERS_VERBOSITY = 'error'
$env:HF_HUB_DISABLE_PROGRESS_BARS = '1'
$env:PYTHONWARNINGS = 'ignore'

try {
    Invoke-RestMethod -Uri 'http://localhost:11434/api/tags' -TimeoutSec 5 | Out-Null
} catch {
    Write-Host 'Ollama is not running. Start the Ollama app (or run: ollama serve) and try again.' -ForegroundColor Red
    exit 1
}

$devices = & uv run --no-sync python -c "import sounddevice as sd; i, o = sd.default.device; print('mic:     ' + sd.query_devices(i)['name']); print('speaker: ' + sd.query_devices(o)['name'])"
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Could not open the audio devices. Run: uv sync --all-packages --extra models --extra tamil' -ForegroundColor Red
    exit 1
}

$name = if ($Lang -eq 'ta') { 'Tamil' } else { 'English' }
Write-Host ''
Write-Host "Semraa M1 live test - $name" -ForegroundColor Cyan
$devices | ForEach-Object { Write-Host "  $_" }
Write-Host '  Use headphones so the AI does not hear itself.' -ForegroundColor Yellow
Write-Host "  Loading models takes about a minute. When it says 'listening', answer the question:"
Write-Host "    `"$Question`""
Write-Host "  Pause for about $([math]::Round($SilenceMs / 1000, 1)) s when you finish; the AI replies out loud."
Write-Host '  Press Ctrl+C to stop.'
Write-Host ''

& uv run --no-sync semraa-spike --silence-ms $SilenceMs run --mic --lang $Lang --llm $Llm --question $Question
exit $LASTEXITCODE
