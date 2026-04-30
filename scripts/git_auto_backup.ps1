# Git Auto Backup (Stash-Pull-Pop Safe Mode) for 20260330
$repoPath = "D:\20260330"
$logFile = "D:\20260330\.git-auto-backup.log"
$intervalSeconds = 300

function Write-Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $msg"
    Write-Host $line
    $line | Add-Content $logFile -Encoding UTF8
}

Set-Location $repoPath
Write-Log "=== Git Auto Backup Started ==="
Write-Log "Repository: $repoPath"
Write-Log ""

while ($true) {
    try {
        Set-Location $repoPath
        $branch = git rev-parse --abbrev-ref HEAD 2>$null
        if ($branch -ne "main") { Write-Log "[SKIP] branch=$branch"; Start-Sleep $intervalSeconds; continue }
        git fetch origin main --quiet 2>$null
        $status = git status --short 2>$null
        if ([string]::IsNullOrWhiteSpace($status)) {
            Write-Log "[CHECK] No local changes."
        } else {
            $changeCount = ($status -split "`n" | Where-Object { $_.Trim() -ne "" }).Count
            Write-Log "[BACKUP] $changeCount changed file(s)."
            $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            git stash push -m "auto-backup-stash-$timestamp" --include-untracked 2>$null
            if ($LASTEXITCODE -ne 0) { throw "git stash failed" }
            Write-Log "[STASH] Saved."
            $behind = git rev-list --count HEAD..origin/main 2>$null
            if ($behind -gt 0) {
                Write-Log "[PULL] origin/main is $behind ahead."
                git pull origin main --quiet 2>$null
                if ($LASTEXITCODE -ne 0) { Write-Log "[ERROR] pull failed"; git stash pop 2>$null; exit 1 }
                Write-Log "[PULL] Synced."
            }
            git stash pop 2>$null
            if ($LASTEXITCODE -ne 0) { Write-Log "[ERROR] pop failed"; exit 1 }
            Write-Log "[POP] Restored."
            $conflicts = git diff --name-only --diff-filter=U 2>$null
            if ($conflicts) { Write-Log "[CONFLICT] $conflicts"; exit 1 }
            git add -A 2>$null
            git commit -m "auto-backup: $timestamp" 2>$null
            if ($LASTEXITCODE -ne 0) { throw "commit failed" }
            git push origin main 2>$null
            if ($LASTEXITCODE -ne 0) { throw "push failed" }
            Write-Log "[DONE] Pushed."
        }
    } catch { Write-Log "[ERROR] $_" }
    Start-Sleep -Seconds $intervalSeconds
}
