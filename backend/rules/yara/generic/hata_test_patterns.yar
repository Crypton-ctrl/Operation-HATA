rule HATA_Demo_Test_Pattern
{
    meta:
        description = "Matches the synthetic HATA demo test marker used to safely demonstrate YARA detection without real malware"
        severity = "LOW"
        author = "Operation HATA"
    strings:
        $marker = "HATA-DEMO-YARA-TEST-PATTERN"
    condition:
        $marker
}

rule Suspicious_Double_Extension_Marker
{
    meta:
        description = "Detects a textual marker suggesting a double-extension trick (e.g. invoice.jpg.exe) referenced within file content"
        severity = "MEDIUM"
        author = "Operation HATA"
    strings:
        $m1 = ".jpg.exe" nocase
        $m2 = ".png.exe" nocase
        $m3 = ".jpeg.scr" nocase
    condition:
        any of them
}
