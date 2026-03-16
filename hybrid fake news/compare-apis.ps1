param(
  [string]$Text,
  [string]$TextFile,
  [switch]$Academic
)

if ([string]::IsNullOrWhiteSpace($Text) -and [string]::IsNullOrWhiteSpace($TextFile)) {
  throw "Provide either -Text or -TextFile."
}

if (-not [string]::IsNullOrWhiteSpace($TextFile)) {
  if (-not (Test-Path $TextFile)) {
    throw "Text file not found: $TextFile"
  }
  $Text = Get-Content -Path $TextFile -Raw
}

$endpoint = if ($Academic) { '/detect-academic' } else { '/detect' }

$targets = @(
  @{ Name = 'LSTM Test Backend'; Url = "http://127.0.0.1:8000$endpoint" },
  @{ Name = 'Transformer Backend'; Url = "http://127.0.0.1:8001$endpoint" },
  @{ Name = 'Hybrid Backend'; Url = "http://127.0.0.1:8002$endpoint" }
)

function Get-ConfidencePercent {
  param($obj)
  if ($null -ne $obj.confidence) { return [math]::Round([double]$obj.confidence * 100, 1) }
  if ($null -ne $obj.lstm -and $null -ne $obj.lstm.confidence) { return [math]::Round([double]$obj.lstm.confidence * 100, 1) }
  return 0.0
}

function Get-Label {
  param($obj)
  if ($null -ne $obj.prediction -and $obj.prediction -ne '') { return [string]$obj.prediction }
  if ($null -ne $obj.lstm -and $null -ne $obj.lstm.label) { return [string]$obj.lstm.label }
  return 'UNKNOWN'
}

function Get-Consensus {
  param($obj)
  if ($null -ne $obj.consensus) { return [string]$obj.consensus }
  return 'n/a'
}

function Get-Source {
  param($obj)
  if ($null -ne $obj.hybrid -and $null -ne $obj.hybrid.source) { return [string]$obj.hybrid.source }
  if ($null -ne $obj.model_used) { return [string]$obj.model_used }
  return 'n/a'
}

function Make-Bar {
  param([double]$percent)
  $blocks = [int][math]::Round($percent / 5)
  if ($blocks -lt 0) { $blocks = 0 }
  if ($blocks -gt 20) { $blocks = 20 }
  $filled = '█' * $blocks
  $empty = '░' * (20 - $blocks)
  return "$filled$empty"
}

$rows = @()

foreach ($target in $targets) {
  try {
    $body = @{ text = $Text } | ConvertTo-Json
    $resp = Invoke-RestMethod -Uri $target.Url -Method Post -Body $body -ContentType 'application/json' -TimeoutSec 60

    $conf = Get-ConfidencePercent -obj $resp
    $rows += [pscustomobject]@{
      Backend    = $target.Name
      Label      = Get-Label -obj $resp
      Confidence = ('{0}%' -f $conf)
      Consensus  = Get-Consensus -obj $resp
      Source     = Get-Source -obj $resp
      Chart      = Make-Bar -percent $conf
      Status     = 'OK'
    }
  }
  catch {
    $rows += [pscustomobject]@{
      Backend    = $target.Name
      Label      = 'ERROR'
      Confidence = '0%'
      Consensus  = 'n/a'
      Source     = 'n/a'
      Chart      = Make-Bar -percent 0
      Status     = $_.Exception.Message
    }
  }
}

Write-Host "`nEndpoint: $endpoint" -ForegroundColor Cyan
$rows | Format-Table Backend, Label, Confidence, Consensus, Source, Chart, Status -AutoSize
