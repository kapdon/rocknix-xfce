"""Parse static readelf evidence; never execute an inspected binary or use ldd."""
import re


def dynamic(text):
    """Accept GNU and elfutils rows. Fail if a relevant row is unrecognized."""
    result = {'needed': [], 'rpath': [], 'runpath': []}
    for line in text.splitlines():
        tag = re.search(r'\b(NEEDED|RUNPATH|RPATH)\b', line)
        if not tag:
            continue
        tail = line[tag.end():].strip()
        if tail.startswith(')') or '[' in tail:
            match = re.search(r'\[([^\]]+)\]\s*$', tail)
            if not match:
                raise ValueError('malformed bracketed dynamic row')
            value = match[1]
        else:
            value = tail
            if not value or any(c.isspace() for c in value):
                raise ValueError('malformed elfutils dynamic row')
        result[tag[1].lower()].append(value)
    if not result['needed']:
        raise ValueError('no dependencies parsed: unsupported output or static ELF')
    return result
