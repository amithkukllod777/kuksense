param(
    [int]$IntervalSeconds = 2,
    [int]$WindowSize = 20,
    [double]$MovementThreshold = 4.0,
    [string]$OutputPath = "./kuksense-rssi.csv"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-WifiSamples {
    $raw = netsh wlan show networks mode=bssid
    $samples = @()
    $ssid = $null

    foreach ($line in $raw) {
        if ($line -match '^\s*SSID\s+\d+\s*:\s*(.*)$') {
            $ssid = $Matches[1].Trim()
            continue
        }

        if ($line -match '^\s*BSSID\s+\d+\s*:\s*([0-9A-Fa-f:]{17})') {
            $bssid = $Matches[1].ToLowerInvariant()
            continue
        }

        if ($line -match '^\s*Signal\s*:\s*(\d+)%' -and $null -ne $bssid) {
            $signalPercent = [int]$Matches[1]
            # Windows exposes percentage, not dBm. This approximation is only for relative movement scoring.
            $estimatedDbm = [math]::Round(($signalPercent / 2.0) - 100.0, 1)
            $samples += [pscustomobject]@{
                TimestampUtc = [DateTime]::UtcNow.ToString("o")
                Ssid         = $ssid
                Bssid        = $bssid
                SignalPct    = $signalPercent
                EstimatedDbm = $estimatedDbm
            }
            $bssid = $null
        }
    }

    return $samples
}

function Get-StdDev([double[]]$Values) {
    if ($Values.Count -lt 2) { return 0.0 }
    $mean = ($Values | Measure-Object -Average).Average
    $sum = 0.0
    foreach ($value in $Values) {
        $sum += [math]::Pow($value - $mean, 2)
    }
    return [math]::Sqrt($sum / ($Values.Count - 1))
}

$history = @{}
$headerWritten = Test-Path $OutputPath

Write-Host "KukSense hardware-free WiFi motion prototype"
Write-Host "Press Ctrl+C to stop. Output: $OutputPath"
Write-Host "This is experimental and detects RF disturbance, not people or vital signs."

while ($true) {
    $samples = Get-WifiSamples

    foreach ($sample in $samples) {
        if (-not $history.ContainsKey($sample.Bssid)) {
            $history[$sample.Bssid] = New-Object System.Collections.Generic.Queue[double]
        }

        $queue = $history[$sample.Bssid]
        $queue.Enqueue([double]$sample.SignalPct)
        while ($queue.Count -gt $WindowSize) {
            [void]$queue.Dequeue()
        }

        $values = @($queue.ToArray())
        $stdDev = [math]::Round((Get-StdDev $values), 2)
        $activityScore = [math]::Round([math]::Min(100.0, ($stdDev / $MovementThreshold) * 100.0), 1)

        $state = if ($queue.Count -lt [math]::Min(8, $WindowSize)) {
            "calibrating"
        } elseif ($stdDev -ge ($MovementThreshold * 1.8)) {
            "high-activity"
        } elseif ($stdDev -ge $MovementThreshold) {
            "possible-movement"
        } else {
            "quiet"
        }

        $row = [pscustomobject]@{
            TimestampUtc  = $sample.TimestampUtc
            Ssid          = $sample.Ssid
            Bssid         = $sample.Bssid
            SignalPct     = $sample.SignalPct
            EstimatedDbm  = $sample.EstimatedDbm
            RollingStdDev = $stdDev
            ActivityScore = $activityScore
            State         = $state
        }

        if (-not $headerWritten) {
            $row | Export-Csv -Path $OutputPath -NoTypeInformation
            $headerWritten = $true
        } else {
            $row | Export-Csv -Path $OutputPath -NoTypeInformation -Append
        }

        Write-Host ("{0} | {1,-18} | {2,3}% | std {3,5} | score {4,5} | {5}" -f \
            (Get-Date -Format "HH:mm:ss"), $sample.Ssid, $sample.SignalPct, $stdDev, $activityScore, $state)
    }

    Start-Sleep -Seconds $IntervalSeconds
}
