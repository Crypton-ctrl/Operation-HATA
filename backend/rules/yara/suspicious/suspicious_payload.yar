rule SuspiciousEmbeddedPayload
{
    meta:
        description = "Detects script or shell interpreter markers concatenated with image data"
        severity = "HIGH"
        author = "Operation HATA"
    strings:
        $php = "<?php"
        $shebang = "#!/bin/"
        $powershell = "powershell -e" nocase
        $eval = "eval(" nocase
        $b64_exec = "base64_decode(" nocase
    condition:
        any of them
}

rule SuspiciousJavaScriptInImage
{
    meta:
        description = "Detects HTML/JavaScript markers embedded in an image file (polyglot indicator)"
        severity = "MEDIUM"
        author = "Operation HATA"
    strings:
        $script = "<script" nocase
        $iframe = "<iframe" nocase
        $onerror = "onerror=" nocase
    condition:
        any of them
}
