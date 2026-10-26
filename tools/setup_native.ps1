# Source dependencies and host compiler for the native Windows build.
# No ROM/BIOS download, administrator access or permanent PATH changes.
param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$localTools = Join-Path $projectRoot 'tools/local'
New-Item -ItemType Directory -Force -Path $localTools | Out-Null
$config = Get-Content -LiteralPath (Join-Path $projectRoot 'config/matching.json') -Raw | ConvertFrom-Json
$hostBin = Join-Path $projectRoot $config.host_tools.directory
$archive = Join-Path $localTools 'w64devkit-x64-2.10.1.7z.exe'
if (-not (Test-Path -LiteralPath (Join-Path $hostBin 'gcc.exe'))) {
    if (-not (Test-Path -LiteralPath $archive)) {
        Invoke-WebRequest -Uri $config.host_tools.archive_url -OutFile $archive
    }
    $actual = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $config.host_tools.archive_sha256) { throw 'Host compiler archive SHA-256 mismatch' }
    # The self-extractor is a GUI executable. Wait explicitly and inspect its
    # own exit code; PowerShell's LASTEXITCODE may still be unset here.
    $extractArgs = '-y -o"' + $localTools + '"'
    $extract = Start-Process -FilePath $archive -ArgumentList $extractArgs -WindowStyle Hidden -Wait -PassThru
    if ($extract.ExitCode -ne 0) { throw 'Host compiler extraction failed' }
}

function Get-PinnedSource([string]$Name, [string]$Url, [string]$Commit) {
    $destination = Join-Path $localTools $Name
    if (-not (Test-Path -LiteralPath $destination)) {
        git clone --config core.autocrlf=false --no-checkout $Url $destination
        if ($LASTEXITCODE -ne 0) { throw "Clone failed: $Name" }
        git -C $destination checkout --detach $Commit
        if ($LASTEXITCODE -ne 0) { throw "Checkout failed: $Name" }
    }
    $head = git -C $destination rev-parse HEAD
    if ($LASTEXITCODE -ne 0 -or $head -ne $Commit) {
        throw "Preserving existing $Name checkout: expected revision $Commit"
    }
    return $destination
}

$translator = Get-PinnedSource 'sp00nz_gbarecomp' 'https://github.com/sp00nznet/gbarecomp.git' 'ac1176f467cbb708f58785e65f36b4f091a8ab20'
$patch = Join-Path $projectRoot 'tools/patches/gbarecomp-native.patch'
git -C $translator apply --reverse --check $patch 2>$null
if ($LASTEXITCODE -ne 0) {
    git -C $translator diff --quiet HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Preserving unrecognized local translator changes' }
    git -C $translator apply --check $patch
    if ($LASTEXITCODE -ne 0) { throw 'Translator patch cannot be applied' }
    git -C $translator apply $patch
    if ($LASTEXITCODE -ne 0) { throw 'Translator patch failed' }
}
$mgba = Get-PinnedSource 'mgba_reference' 'https://github.com/mgba-emu/mgba.git' 'fd9dc5c2cbf234365068855851107e762fc6211b'
git -C $mgba diff --quiet HEAD
if ($LASTEXITCODE -ne 0) { throw 'Preserving local changes to mGBA sources' }
$venv = Join-Path $projectRoot '.venv'
if (-not (Test-Path -LiteralPath (Join-Path $venv 'Scripts/python.exe'))) {
    & $Python -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Python virtual environment creation failed' }
}
& (Join-Path $venv 'Scripts/python.exe') -m pip install -r (Join-Path $projectRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Native build Python dependency installation failed' }
Write-Output 'Native dependencies ready. Run: .\tools\build_native.ps1'
