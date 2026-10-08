rule Embedded_Windows_Executable
{
    meta:
        description = "Detects a Windows PE executable embedded or disguised within another file"
        severity = "CRITICAL"
        author = "Operation HATA"
    strings:
        $mz = "MZ"
        $pe = "PE\x00\x00"
        $dos_stub = "This program cannot be run in DOS mode"
    condition:
        $mz at 0 or ($mz and $pe and $dos_stub)
}

rule Embedded_ELF_Executable
{
    meta:
        description = "Detects an ELF (Linux) executable embedded within another file"
        severity = "CRITICAL"
        author = "Operation HATA"
    strings:
        $elf = { 7F 45 4C 46 }
    condition:
        $elf
}

rule Embedded_ZIP_Archive
{
    meta:
        description = "Detects a ZIP archive local file header appended to the file"
        severity = "MEDIUM"
        author = "Operation HATA"
    strings:
        $zip = { 50 4B 03 04 }
    condition:
        $zip
}
