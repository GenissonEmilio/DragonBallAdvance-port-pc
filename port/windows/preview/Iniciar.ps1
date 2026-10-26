param([string]$Rom = '', [int]$Frames = 0, [switch]$Headless, [switch]$NoAudio)
$ErrorActionPreference = 'Stop'
try {
    $binary = Join-Path $PSScriptRoot 'dbaa_game.exe'
    if (-not (Test-Path -LiteralPath $binary)) { throw 'dbaa_game.exe nao encontrado. Extraia o ZIP completo antes de jogar.' }
    if (-not $Rom) {
        $Rom = Join-Path $PSScriptRoot 'baserom.gba'
        if (-not (Test-Path -LiteralPath $Rom)) {
            Add-Type -AssemblyName System.Windows.Forms
            $picker = New-Object System.Windows.Forms.OpenFileDialog
            $picker.Title = 'Selecione sua ROM USA de Dragon Ball: Advanced Adventure'
            $picker.Filter = 'ROM de Game Boy Advance (*.gba)|*.gba'
            try {
                if ($picker.ShowDialog() -ne 'OK') { exit 0 }
                $Rom = $picker.FileName
            } finally { $picker.Dispose() }
        }
    }
    $Rom = (Resolve-Path -LiteralPath $Rom).Path
    # Use .NET directly: the Windows PowerShell launched from PS 7 can inherit
    # a module path where Get-FileHash is unavailable.
    $romStream = [System.IO.File]::OpenRead($Rom)
    $sha1 = [System.Security.Cryptography.SHA1]::Create()
    try {
        $hash = [System.BitConverter]::ToString($sha1.ComputeHash($romStream)).Replace('-', '').ToLowerInvariant()
    } finally { $sha1.Dispose(); $romStream.Dispose() }
    if ($hash -ne '1338584d8cfa57402603197e65d2e2ff0184d24f') {
        throw 'ROM incompativel. Esta previa exige a versao USA BDVE rev0, SHA1 1338584d8cfa57402603197e65d2e2ff0184d24f.'
    }
    $logs = Join-Path $PSScriptRoot 'logs'
    New-Item -ItemType Directory -Force -Path $logs | Out-Null
    . (Join-Path $PSScriptRoot 'Sessoes.ps1')
    $session = New-DbaaDiagnosticSession -Root $logs
    $env:DBAA_NATIVE_REPORT = Join-Path $session 'native.json'
    $env:DBAA_GAME_AUDIO_REPORT = Join-Path $session 'audio.json'
    $env:DBAA_GAME_AUDIO_DEVICE = if ($NoAudio) { '0' } else { '1' }
    # Captures are opt-in for developers; do not inherit a multi-GB PCM dump.
    Remove-Item Env:DBAA_GAME_PCM -ErrorAction SilentlyContinue
    Remove-Item Env:GBA_VALIDATE -ErrorAction SilentlyContinue
    $gameArgs = @($Rom)
    if ($Frames -gt 0) { $gameArgs += @('--frames', [string]$Frames) }
    if ($Headless) { $gameArgs += '--headless' }
    Write-Host 'Previa de desenvolvimento. Setas: mover | Z: A | X: B | Enter: Start'
    Write-Host ('Save: ' + [System.IO.Path]::ChangeExtension($Rom, '.eep'))
    Write-Host ('Diagnosticos: ' + $session)
    # Native stderr is a diagnostic stream, not a PowerShell terminating error.
    $ErrorActionPreference = 'Continue'
    & $binary @gameArgs 1> (Join-Path $session 'stdout.log') 2> (Join-Path $session 'stderr.log')
    $gameResult = $LASTEXITCODE
    if ($gameResult -ne 0) {
        Write-Host ('O jogo encerrou com erro ' + $gameResult + '. Envie os arquivos desta sessao em logs ao relatar o problema.')
    }
    exit $gameResult
} catch {
    Write-Host $_.Exception.Message
    exit 2
}
