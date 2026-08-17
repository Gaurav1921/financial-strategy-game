# Joint Venture betrayal-viability simulation.
# Tests whether reputation-aware / endgame-aware strategies actually beat
# blind backstabbing across a season, and sweeps drain_bonus / growth_rate
# to find parameter ranges where the "Consortium" design holds up.

function Test-Willing {
    param([string]$Strategy, [int]$PartnerDrainCount)
    switch ($Strategy) {
        "Loyalist"         { return $true }
        "Backstabber"      { return $true }
        "ReputationAware"  { return ($PartnerDrainCount -eq 0) }
        "Grudger"          { return ($PartnerDrainCount -le 1) }
        "Opportunist"      { return $true }
        "EndgameRational"  { return ($PartnerDrainCount -eq 0) }
    }
}

function Test-Drain {
    param([string]$Strategy, [bool]$IsFinal, [int]$PartnerDrainCount, [int]$RoundsHeld)
    switch ($Strategy) {
        "Loyalist"         { return $false }
        "Backstabber"      { return ($RoundsHeld -ge 1) }
        "ReputationAware"  { return $false }
        "Grudger"          { return $false }
        "Opportunist"      { if ($PartnerDrainCount -gt 0) { return $true } elseif ($IsFinal) { return $true } else { return $false } }
        "EndgameRational"  { return $IsFinal }
    }
}

$strategies   = @("Loyalist","Backstabber","ReputationAware","Grudger","Opportunist","EndgameRational")
$numTrials    = 250
$rounds       = 20
$startCash    = 100.0
$contribution = 10.0
$idleYield    = 1.0

$drainBonusValues  = @(0.50, 0.65, 0.80, 0.95)
$growthRateValues  = @(0.05, 0.10, 0.15, 0.20)

$results = New-Object System.Collections.ArrayList

foreach ($drainBonus in $drainBonusValues) {
  foreach ($growthRate in $growthRateValues) {

    $totalNetWorth = @{}
    $winCount = @{}
    foreach ($s in $strategies) { $totalNetWorth[$s] = 0.0; $winCount[$s] = 0 }

    for ($trial = 0; $trial -lt $numTrials; $trial++) {
        $n = $strategies.Count
        $cash = New-Object 'double[]' $n
        $drainCount = New-Object 'int[]' $n
        $inJV = New-Object 'bool[]' $n
        for ($i = 0; $i -lt $n; $i++) { $cash[$i] = $startCash; $drainCount[$i] = 0; $inJV[$i] = $false }

        $activeJVs = New-Object System.Collections.ArrayList

        for ($round = 1; $round -le $rounds; $round++) {
            $isFinal = ($round -eq $rounds)

            $free = New-Object System.Collections.ArrayList
            for ($i = 0; $i -lt $n; $i++) { if (-not $inJV[$i]) { [void]$free.Add($i) } }
            $freeShuffled = $free | Sort-Object { Get-Random }
            $freeArr = @($freeShuffled)

            for ($k = 0; $k -lt $freeArr.Count - 1; $k += 2) {
                $a = $freeArr[$k]; $b = $freeArr[$k+1]
                $aWilling = Test-Willing $strategies[$a] $drainCount[$b]
                $bWilling = Test-Willing $strategies[$b] $drainCount[$a]
                if ($aWilling -and $bWilling) {
                    $cash[$a] -= $contribution
                    $cash[$b] -= $contribution
                    $maxDur = Get-Random -Minimum 2 -Maximum 7
                    $jv = @{ a = $a; b = $b; pot = 2 * $contribution; roundsHeld = 0; maxDur = $maxDur }
                    [void]$activeJVs.Add($jv)
                    $inJV[$a] = $true; $inJV[$b] = $true
                }
            }

            for ($i = 0; $i -lt $n; $i++) { if (-not $inJV[$i]) { $cash[$i] += $idleYield } }

            $stillActive = New-Object System.Collections.ArrayList
            foreach ($jv in $activeJVs) {
                $a = $jv.a; $b = $jv.b
                $jv.pot = $jv.pot * (1 + $growthRate)
                $jv.roundsHeld = $jv.roundsHeld + 1

                $drainA = Test-Drain $strategies[$a] $isFinal $drainCount[$b] $jv.roundsHeld
                $drainB = Test-Drain $strategies[$b] $isFinal $drainCount[$a] $jv.roundsHeld

                if ($drainA -and $drainB) {
                    $cash[$a] += 0.4 * $jv.pot; $cash[$b] += 0.4 * $jv.pot
                    $drainCount[$a] += 1; $drainCount[$b] += 1
                    $inJV[$a] = $false; $inJV[$b] = $false
                } elseif ($drainA) {
                    $cash[$a] += $drainBonus * $jv.pot; $cash[$b] += (1 - $drainBonus) * $jv.pot
                    $drainCount[$a] += 1
                    $inJV[$a] = $false; $inJV[$b] = $false
                } elseif ($drainB) {
                    $cash[$b] += $drainBonus * $jv.pot; $cash[$a] += (1 - $drainBonus) * $jv.pot
                    $drainCount[$b] += 1
                    $inJV[$a] = $false; $inJV[$b] = $false
                } elseif ($jv.roundsHeld -ge $jv.maxDur -or $isFinal) {
                    $cash[$a] += 0.5 * $jv.pot; $cash[$b] += 0.5 * $jv.pot
                    $inJV[$a] = $false; $inJV[$b] = $false
                } else {
                    [void]$stillActive.Add($jv)
                }
            }
            $activeJVs = $stillActive
        }

        $best = -1; $bestVal = [double]::MinValue
        for ($i = 0; $i -lt $n; $i++) {
            $totalNetWorth[$strategies[$i]] += $cash[$i]
            if ($cash[$i] -gt $bestVal) { $bestVal = $cash[$i]; $best = $i }
        }
        $winCount[$strategies[$best]] += 1
    }

    foreach ($s in $strategies) {
        $avgNW = $totalNetWorth[$s] / $numTrials
        $winRate = 100.0 * $winCount[$s] / $numTrials
        [void]$results.Add([PSCustomObject]@{
            DrainBonus  = $drainBonus
            GrowthRate  = $growthRate
            Strategy    = $s
            AvgNetWorth = [math]::Round($avgNW,1)
            WinRatePct  = [math]::Round($winRate,1)
        })
    }
  }
}

$results | Export-Csv -Path "d:\Game\sim\results.csv" -NoTypeInformation
Write-Output "DONE. $($results.Count) rows written to d:\Game\sim\results.csv"
