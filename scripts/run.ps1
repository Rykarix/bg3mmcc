$CWD = (Get-Location).Path

if (-Not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "UV is not installed. Installing UV..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
} else {
    Write-Host "UV is already installed. Skipping installation."
}

$venvPath = "$CWD\.venv"
if (-Not (Test-Path $venvPath)) {
    Write-Host ".venv folder not found. Setting up virtual environment..."
    uv venv
    uv sync
} else {
    Write-Host ".venv folder already exists. Skipping setup."
}

Write-Host "Everything has setup correctly. You have a 2 things left to do."
Write-Host "1: Add the files to compare to $CWD\data\settings_json"
Write-Host "2: run the command 'uv run bg3mmcc.py --hosts-file=HOSTS_JSON_FILENAME.json'. DO NOT FORGET: change 'HOSTS_JSON_FILENAME.json' with the ACTUAL name of the file."
