# SPDX-License-Identifier: GPL-3.0-or-later
# Adapted from Port_DumpState_CreateDirectoryAt / DumpNumber / SaveDumpCounter:
# EstebanPdN/zelda-tmc-3ds, src/port/port_dump_state.c
# Revision 2f248e06ff1e320da8e2d97ef2fe0202a2071fff.
# Copyright (C) 2026 Project Picori contributors; 3DS maintenance Esteban PDN.
# Windows/PowerShell adaptation: persistent numbered log sessions, no game state.
# GPL-3.0 text: third_party/zelda-GPL-3.0.txt in the preview package.

function New-DbaaDiagnosticSession {
    param([Parameter(Mandatory=$true)][string]$Root,
          [string]$Stamp = (Get-Date -Format 'yyyyMMdd-HHmmss'))
    if ($Stamp -notmatch '^\d{8}-\d{6}$') { throw 'Invalid diagnostic timestamp' }
    [void][System.IO.Directory]::CreateDirectory($Root)
    $Root = [System.IO.Path]::GetFullPath($Root)
    # Serialize allocation across launcher processes; timestamps alone can repeat.
    $guard = $null
    for ($attempt = 0; $attempt -lt 100 -and $null -eq $guard; $attempt++) {
        try {
            $guard = [System.IO.File]::Open((Join-Path $Root '.session.lock'),
                [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite,
                [System.IO.FileShare]::None)
        } catch [System.IO.IOException] { Start-Sleep -Milliseconds 20 }
    }
    if ($null -eq $guard) { throw 'Another launcher is allocating its diagnostic session' }
    try {
        $counter = Join-Path $Root 'dump-sequence.txt'
        [uint64]$next = 0
        if ([System.IO.File]::Exists($counter)) {
            $text = [System.IO.File]::ReadAllText($counter).Trim()
            [uint32]$stored = 0
            if ([uint32]::TryParse($text, [ref]$stored)) { $next = $stored }
        }
        $hasSessions = $false
        foreach ($directory in [System.IO.Directory]::EnumerateDirectories($Root)) {
            $name = [System.IO.Path]::GetFileName($directory)
            if ($name -match '^(\d{3,})(?:-dump-.*)?$') {
                [uint32]$number = 0
                if ([uint32]::TryParse($Matches[1], [ref]$number)) {
                    $hasSessions = $true
                    if ($number -eq [uint32]::MaxValue) { throw 'Diagnostic sequence exhausted' }
                    if ($number -ge $next) { $next = [uint64]$number + 1 }
                }
            }
        }
        if (-not $hasSessions) { $next = 0 }
        if ($next -ge [uint32]::MaxValue) { throw 'Diagnostic sequence exhausted' }
        $session = Join-Path $Root (('{0:D3}' -f $next) + '-dump-' + $Stamp)
        if ([System.IO.Directory]::Exists($session)) { throw 'Diagnostic allocation collision' }
        [void][System.IO.Directory]::CreateDirectory($session)
        # A counter-write failure does not discard the capture: directory scanning
        # recovers the next number on a subsequent launch, as in the source port.
        try {
            $temporary = $counter + '.tmp'
            [System.IO.File]::WriteAllText($temporary, ([string]($next + 1) + "`n"))
            if ([System.IO.File]::Exists($counter)) {
                # PowerShell binds $null to an empty string for this overload.
                # A named backup works in both Windows PowerShell and PS 7.
                [System.IO.File]::Replace($temporary, $counter, ($counter + '.bak'))
            } else { [System.IO.File]::Move($temporary, $counter) }
        } catch { Write-Warning 'Session created; sequence counter will be recovered from directories' }
        return $session
    } finally { $guard.Dispose() }
}
