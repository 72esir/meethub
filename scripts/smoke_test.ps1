param(
    [string]$GatewayUrl = "http://localhost:8080",
    [string]$AuthUrl = "http://localhost:8001",
    [string]$UploadUrl = "http://localhost:8002",
    [string]$FeedUrl = "http://localhost:8003",
    [string]$ModerationUrl = "http://localhost:8004",
    [string]$AdminToken = "123",
    [Parameter(Mandatory = $true)]
    [string]$VideoPath,
    [int]$UploadPollAttempts = 20,
    [int]$UploadPollDelaySeconds = 3,
    [int]$ModerationPollAttempts = 20,
    [int]$ModerationPollDelaySeconds = 3,
    [int]$FeedPollAttempts = 20,
    [int]$FeedPollDelaySeconds = 3
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-Json {
    param(
        [ValidateSet("GET", "POST", "PUT", "DELETE")]
        [string]$Method,
        [string]$Uri,
        [hashtable]$Headers = @{},
        [object]$Body = $null
    )

    $params = @{
        Method  = $Method
        Uri     = $Uri
        Headers = $Headers
    }

    if ($null -ne $Body) {
        $params.ContentType = "application/json"
        $params.Body = ($Body | ConvertTo-Json -Compress -Depth 10)
    }

    return Invoke-RestMethod @params
}

function Wait-Until {
    param(
        [scriptblock]$Action,
        [scriptblock]$Condition,
        [int]$Attempts,
        [int]$DelaySeconds,
        [string]$Description
    )

    for ($i = 1; $i -le $Attempts; $i++) {
        $result = & $Action
        if (& $Condition $result) {
            return $result
        }
        Start-Sleep -Seconds $DelaySeconds
    }

    throw "Timeout while waiting for: $Description"
}

if (-not (Test-Path -LiteralPath $VideoPath)) {
    throw "Video file not found: $VideoPath"
}

$fileName = [System.IO.Path]::GetFileName($VideoPath)
$runId = [guid]::NewGuid().ToString("N").Substring(0, 8)
$email = "smoke_$runId@example.com"
$username = "smoke_$runId"
$password = "password123"

Write-Step "Checking health endpoints"
Invoke-WebRequest -UseBasicParsing "$GatewayUrl/healthz" | Out-Null
Invoke-Json -Method GET -Uri "$AuthUrl/health" | Out-Null
Invoke-Json -Method GET -Uri "$AuthUrl/ready" | Out-Null
Invoke-Json -Method GET -Uri "$UploadUrl/health" | Out-Null
Invoke-Json -Method GET -Uri "$UploadUrl/ready" | Out-Null
Invoke-Json -Method GET -Uri "$FeedUrl/health" | Out-Null
Invoke-Json -Method GET -Uri "$FeedUrl/ready" | Out-Null
Invoke-Json -Method GET -Uri "$ModerationUrl/health" | Out-Null
Invoke-Json -Method GET -Uri "$ModerationUrl/ready" | Out-Null

Write-Step "Registering user $email"
$register = Invoke-Json -Method POST -Uri "$AuthUrl/auth/register" -Body @{
    email    = $email
    password = $password
    username = $username
}

$accessToken = $register.access_token
$refreshToken = $register.refresh_token
$authHeaders = @{ Authorization = "Bearer $accessToken" }

Write-Step "Fetching current profile"
$me = Invoke-Json -Method GET -Uri "$AuthUrl/auth/me" -Headers $authHeaders
$userId = $me.id

Write-Step "Requesting upload session"
$uploadRequest = Invoke-Json -Method POST -Uri "$UploadUrl/upload/request" -Headers $authHeaders -Body @{
    file_name    = $fileName
    content_type = "video/mp4"
}

$uploadId = $uploadRequest.upload_id
$presignedUploadUrl = $uploadRequest.upload_url

Write-Step "Uploading binary to presigned URL"
Invoke-WebRequest -UseBasicParsing -Method Put -Uri $presignedUploadUrl -InFile $VideoPath -ContentType "video/mp4" | Out-Null

Write-Step "Completing upload"
Invoke-Json -Method POST -Uri "$UploadUrl/upload/complete" -Headers $authHeaders -Body @{
    upload_id   = $uploadId
    description = "Smoke test video $runId"
    hashtags    = @("smoke", "mvp", $runId)
} | Out-Null

Write-Step "Waiting for upload status to reach ready or error"
$uploadStatus = Wait-Until `
    -Action { Invoke-Json -Method GET -Uri "$UploadUrl/upload/status/$uploadId" -Headers $authHeaders } `
    -Condition { param($result) $result.status -in @("ready", "error") } `
    -Attempts $UploadPollAttempts `
    -DelaySeconds $UploadPollDelaySeconds `
    -Description "upload processing completion"

if ($uploadStatus.status -eq "error") {
    throw "Upload failed: $($uploadStatus.error_message)"
}

Write-Step "Waiting for moderation queue item"
$moderationItem = Wait-Until `
    -Action { Invoke-Json -Method GET -Uri "$ModerationUrl/moderation/pending" -Headers @{ "X-Admin-Token" = $AdminToken } } `
    -Condition {
        param($result)
        @($result) | Where-Object { $_.video_id -eq $uploadId } | Select-Object -First 1
    } `
    -Attempts $ModerationPollAttempts `
    -DelaySeconds $ModerationPollDelaySeconds `
    -Description "moderation item for uploaded video"

$moderationMatch = @($moderationItem) | Where-Object { $_.video_id -eq $uploadId } | Select-Object -First 1
if ($null -eq $moderationMatch) {
    throw "Moderation item for upload $uploadId was not created"
}

$moderationId = $moderationMatch.id
$videoId = $moderationMatch.video_id

Write-Step "Approving moderation item $moderationId"
Invoke-Json -Method POST -Uri "$ModerationUrl/moderation/$moderationId/approve" -Headers @{ "X-Admin-Token" = $AdminToken } | Out-Null

Write-Step "Waiting for video to appear in For You feed"
$feedResult = Wait-Until `
    -Action { Invoke-Json -Method GET -Uri "$FeedUrl/feed/foryou" -Headers $authHeaders } `
    -Condition {
        param($result)
        @($result.items) | Where-Object { $_.id -eq $videoId } | Select-Object -First 1
    } `
    -Attempts $FeedPollAttempts `
    -DelaySeconds $FeedPollDelaySeconds `
    -Description "video appearance in feed"

$feedVideo = @($feedResult.items) | Where-Object { $_.id -eq $videoId } | Select-Object -First 1
if ($null -eq $feedVideo) {
    throw "Approved video $videoId did not appear in feed"
}

Write-Step "Checking video endpoint and interactions"
Invoke-Json -Method GET -Uri "$FeedUrl/videos/$videoId" -Headers $authHeaders | Out-Null
Invoke-Json -Method POST -Uri "$FeedUrl/videos/$videoId/like" -Headers $authHeaders | Out-Null
Invoke-Json -Method POST -Uri "$FeedUrl/videos/$videoId/view" -Headers $authHeaders | Out-Null
Invoke-Json -Method GET -Uri "$FeedUrl/users/$userId/videos" -Headers $authHeaders | Out-Null

Write-Step "Smoke test completed"
[pscustomobject]@{
    user_id       = $userId
    upload_id     = $uploadId
    video_id      = $videoId
    moderation_id = $moderationId
    feed_status   = "ok"
    upload_status = $uploadStatus.status
}
