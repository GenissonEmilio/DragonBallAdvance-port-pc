# Local Windows toolchain. No administrator access or permanent PATH changes.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$toolConfig = Get-Content -LiteralPath (Join-Path $projectRoot 'config/matching.json') -Raw | ConvertFrom-Json
$localTools = Join-Path $projectRoot 'tools/local'
New-Item -ItemType Directory -Force -Path $localTools | Out-Null

function Get-CheckedArchive($Url, $FileName, $ExpectedHash) {
    $archivePath = Join-Path $localTools $FileName
    if (-not (Test-Path -LiteralPath $archivePath)) {
        Invoke-WebRequest -Uri $Url -OutFile $archivePath
    }
    $actualHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -ne $ExpectedHash) { throw "SHA-256 mismatch: $archivePath" }
    return $archivePath
}

Push-Location $projectRoot
$savedPath = $env:PATH
try {
    $hostArchive = Get-CheckedArchive $toolConfig.host_tools.archive_url 'w64devkit-x64-2.10.1.7z.exe' $toolConfig.host_tools.archive_sha256
    $armArchive = Get-CheckedArchive $toolConfig.arm_tools.archive_url 'gcc-arm-none-eabi-8-2018-q4-major-windows.tar.bz2' $toolConfig.arm_tools.archive_sha256
    $hostBin = Join-Path $projectRoot $toolConfig.host_tools.directory
    if (-not (Test-Path -LiteralPath (Join-Path $hostBin 'gcc.exe'))) {
        # This is the published w64devkit console self-extractor; switches suppress prompts.
        & $hostArchive -y "-o$localTools"
        if ($LASTEXITCODE -ne 0) { throw 'w64devkit extraction failed' }
    }
    $armBin = Join-Path $projectRoot $toolConfig.arm_tools.directory
    if (-not (Test-Path -LiteralPath (Join-Path $armBin 'arm-none-eabi-as.exe'))) {
        tar.exe -xf $armArchive -C $localTools
        if ($LASTEXITCODE -ne 0) { throw 'ARM tool extraction failed' }
    }
    $compilerSource = Join-Path $localTools 'agbcc'
    if (-not (Test-Path -LiteralPath $compilerSource)) {
        git clone --no-checkout $toolConfig.compiler.source_url $compilerSource
        if ($LASTEXITCODE -ne 0) { throw 'agbcc clone failed' }
        git -C $compilerSource checkout --detach $toolConfig.compiler.source_commit
        if ($LASTEXITCODE -ne 0) { throw 'agbcc checkout failed' }
    }
    $actualCommit = git -C $compilerSource rev-parse HEAD
    if ($LASTEXITCODE -ne 0 -or $actualCommit -ne $toolConfig.compiler.source_commit) {
        throw 'Existing agbcc checkout has another revision; preserve it and use the revision in matching.json.'
    }
    git -C $compilerSource diff --quiet HEAD -- gcc
    if ($LASTEXITCODE -ne 0) { throw 'agbcc compiler sources contain local changes' }
    $env:PATH = $hostBin + ';' + $savedPath
    $compilerOutput = Join-Path $projectRoot $toolConfig.compiler.path
    if (-not (Test-Path -LiteralPath $compilerOutput)) {
        & (Join-Path $hostBin 'make.exe') -C (Join-Path $compilerSource 'gcc') -j1
        if ($LASTEXITCODE -ne 0) { throw 'agbcc build failed' }
    }
    Write-Output 'Matching toolchain ready. Run: python tools/match.py'
} finally {
    $env:PATH = $savedPath
    Pop-Location
}
