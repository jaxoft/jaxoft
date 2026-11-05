# === CONFIG ===
$Source = "D:\Photos-telefoon\Photos-TelefoonJack"   # <-- map 1 #Leeg !
$Dest   = "C:\Users\j_w_1\OneDrive\Afbeeldingen\SD-kaart"   # <-- map 2 

$DestNew = "C:\Users\j_w_1\OneDrive\Afbeeldingen\Samsung Gallery\DCIM\Camera"

# ==============

# Maak check-folder aan in SOURCE
$CheckFolder = Join-Path $Source "check"
New-Item -ItemType Directory -Path $CheckFolder -Force | Out-Null

# Tijdelijke lijsten
$SourceList = "$env:TEMP\source_files.txt"
$DestList   = "$env:TEMP\dest_files.txt"

Write-Host "Maken van bestandslijsten..."

# Source lijst (alle foto's in de source folder)
Get-ChildItem -Path $Source -Recurse -Include *.jpg,*.jpeg,*.png |
    ForEach-Object { $_.Name } |  # Alleen de bestandsnaam
    Sort-Object |
    Out-File $SourceList -Encoding utf8

# Dest lijst (alle foto's in de destination folder)
$destFiles = Get-ChildItem -Path $Dest -Recurse -Include *.jpg,*.jpeg,*.png
if ($destFiles) {
    $destFiles |
        ForEach-Object { $_.Name } |  # Alleen de bestandsnaam
        Sort-Object |
        Out-File $DestList -Encoding utf8
} else {
    Write-Host "Geen bestanden gevonden in de destination folder: $Dest" -ForegroundColor Yellow
    Set-Content -Path $DestList -Value ""  # Maak een leeg bestand
}

write-host $SourceList
write-host $DestList

Write-Host "Vergelijken..."

# Controleer of de lijsten bestaan en niet leeg zijn
if (-Not (Test-Path $SourceList) -or -Not (Test-Path $DestList) -or (Get-Content $DestList).Count -eq 0) {
    Write-Host "Geen bestanden om te vergelijken. Controleer de source en destination folders." -ForegroundColor Red
    exit
}

# Vind ontbrekende bestanden
$missing = Compare-Object `
    -ReferenceObject (Get-Content $SourceList) `
    -DifferenceObject (Get-Content $DestList) `
    -PassThru |
    Where-Object { $_.SideIndicator -eq '<=' }

Write-Host "`nOntbrekende bestanden gevonden: $($missing.Count)" -ForegroundColor Cyan

foreach ($fileName in $missing) {
    # Zoek het bestand in de source folder
    $sourceFile = Get-ChildItem -Path $Source -Recurse -Include $fileName | Select-Object -First 1
    if ($sourceFile) {
        $targetFile = Join-Path $CheckFolder $fileName
        Write-Host "Kopiëren: $sourceFile -> $targetFile"

        # Kopieer bestand naar de check folder
        # Copy-Item -Path $sourceFile.FullName -Destination $targetFile -Force
    }
}

Write-Host "`nKlaar! De ontbrekende bestanden staan nu in: `n$CheckFolder" -ForegroundColor Green