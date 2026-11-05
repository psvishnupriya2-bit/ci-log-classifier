import re

NOISE = ("using cached", "collecting ", "downloading ", "requirement already satisfied",
         "installing collected", "successfully installed", "obtaining ", "building wheel",
         "preparing metadata", "hint:", "##[group]", "##[endgroup]", "##[command]",
         "stop and remove container", "remove container network", "cleaning up orphan",
         "post job cleanup", "from https", "remote:", "* [new", "to https",
         "git version", "deleting", "temporarily overriding", "adding repository")

def clean(text):
    kept = []
    for line in text.splitlines():
        l = re.sub(r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z ?", "", line)
        l = re.sub(r"(\x1b)?\[[0-9;]*m", "", l).strip()
        low = l.lower()
        if not low or low.startswith(NOISE) or ".whl" in low:
            continue
        kept.append(l)
    text = "\n".join(kept)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"(?<!\w)(?:[A-Za-z]:\\|\.{0,2}/|~/)[\w\-.@+/\\]+", " ", text)
    text = re.sub(r"\b[0-9a-f]{7,64}\b", " ", text)
    text = re.sub(r"\b\d+(\.\d+)*\b", " ", text)
    lines = []
    for line in text.lower().splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)
