rule Polyglot_JPEG_PDF
{
    meta:
        description = "Detects a JPEG file that also contains a valid PDF header (JPEG/PDF polyglot technique)"
        severity = "HIGH"
        author = "Operation HATA"
    strings:
        $jpeg_header = { FF D8 FF }
        $pdf_header = "%PDF-"
    condition:
        $jpeg_header at 0 and $pdf_header
}

rule Polyglot_PNG_ZIP
{
    meta:
        description = "Detects a PNG file that also contains a ZIP local file header (PNG/ZIP polyglot technique)"
        severity = "HIGH"
        author = "Operation HATA"
    strings:
        $png_header = { 89 50 4E 47 0D 0A 1A 0A }
        $zip_header = { 50 4B 03 04 }
    condition:
        $png_header at 0 and $zip_header
}
