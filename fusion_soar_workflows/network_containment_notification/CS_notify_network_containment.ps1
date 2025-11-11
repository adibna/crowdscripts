# Valida arquivos e exibe notificação de contenção de máquina ao usuário logado

$Log    = 'C:\Windows\TEMP\CS_notify_log.txt'
$Logo   = 'C:\Windows\TEMP\CS_company_logo.png'
$Html   = 'C:\Windows\TEMP\CS_notify_network_containment.html'
$Script = 'C:\Windows\TEMP\CS_notify_network_containment.cmd'

function Write-log ($message){
    try{
        "$(Get-Date -f 'yyyy-MM-dd HH:mm:ss') $message" | Add-Content $Log
    }catch{
        
    } 
}


# Aguarda por até 5 minutos para receber e validar os arquivos necessários
$sw = [Diagnostics.Stopwatch]::StartNew()
while ($true) {
    if ((Test-Path $Logo) -and (Test-Path $Html) -and (Test-Path $Script)) { break }
    Start-Sleep 3
    if ($sw.Elapsed.TotalMinutes -ge 5) { break }
}

# Validação do usuário com sessão ativa
function Get-ActiveUserAndSession {
    $raw = (quser) 2>$null
    if (-not $raw) { return $null }

    $lines = $raw -split "`r?`n" | Where-Object { $_ -and ($_ -notmatch 'USERNAME|\-+') }
    $active = $lines | Where-Object { $_ -match '\bActive\b' -or $_ -match '\bAtivo\b' } | Select-Object -First 1
    if (-not $active) { return $null }

    # Normalize spacing
    $line = $active -replace '^\s+','' -replace '\s+',' '
    $parts = $line -split ' '

    # Typical columns: USERNAME SESSIONNAME ID STATE IDLE LOGON TIME
    $username = $parts[0].Trim()           # may be ">user", "DOMAIN\user", or "user@domain"
    $username = $username.TrimStart('>')   # remove leading '>' from active row
    $sessionId = [int]$parts[2]

    # Build an /RU that schtasks can resolve:
    # - If already DOMAIN\user or user@domain, keep it.
    # - Else prefix with the AD domain (if joined) or local computer name.
    $ru = $username
    if ($ru -notmatch '\\' -and $ru -notmatch '@') {
        $sys = Get-CimInstance Win32_ComputerSystem
        $domain = $sys.Domain
        $joined = $sys.PartOfDomain
        if ($joined -and $domain -and $domain -ne $sys.Name) {
            $ru = "$domain\$ru"
        } else {
            $ru = "$($sys.Name)\$ru"  # local account
        }
    }

    [pscustomobject]@{
        User          = $username
        RunAsUser     = $ru
        SessionId     = $sessionId
        Line          = $active
    }
}

$usr = Get-ActiveUserAndSession
if (-not $usr) {
    Write-log "No active session found. Falling back to msg.exe."
    try { & "$env:windir\System32\msg.exe" * "Seu dispositivo foi CONTIDO pelo CrowdStrike. Contate a TI: (00) 1234-5678." } catch {}
    exit 1
}

Write-log "Active session: user=$($usr.User) id=$($usr.SessionId) line='$($usr.Line)'"
Write-log "Resolved /RU for schtasks: $($usr.RunAsUser)"

# --- Create and run the one-shot interactive task ---
$taskName = "FalconNotify_$($usr.SessionId)_$PID"

# Ensure the time is in the future; Schedule at +1 minute (24h format)
$startAt  = (Get-Date).AddMinutes(1).ToString('HH:mm')

# IMPORTANT: quote the /TR path; schtasks is picky with spaces.
$createArgs = @(
    '/Create',
    '/SC','ONCE',
    '/TN',$taskName,
    '/TR',('"' + $Script + '"'),
    '/ST',$startAt,
    '/F',
    '/RL','HIGHEST',
    '/RU',$usr.RunAsUser,
    '/IT'
)

Write-log "schtasks.exe $($createArgs -join ' ')"
$create = Start-Process -FilePath "$env:windir\System32\schtasks.exe" -ArgumentList $createArgs -Wait -NoNewWindow -PassThru

# If creation failed, bail early so we don’t spam extra errors
if ($create.ExitCode -ne 0) {
    Write-log "Task creation failed with ExitCode $($create.ExitCode)."
    exit 1
}

$runArgs = @('/Run','/TN',$taskName)
Write-log "schtasks.exe $($runArgs -join ' ')"
$null = Start-Process -FilePath "$env:windir\System32\schtasks.exe" -ArgumentList $runArgs -Wait -NoNewWindow -PassThru

Start-Sleep 3
$delArgs = @('/Delete','/TN',$taskName,'/F')
Write-log "schtasks.exe $($delArgs -join ' ')"
$null = Start-Process -FilePath "$env:windir\System32\schtasks.exe" -ArgumentList $delArgs -Wait -NoNewWindow -PassThru

exit 0
