
#!/usr/bin/env python3
import argparse, hashlib, os, subprocess, sys
from pathlib import Path
from fnmatch import fnmatch
import yaml
from lxml import etree

def run(cmd, capture=False, check=True):
    if capture:
        return subprocess.run(cmd, check=check, stdout=subprocess.PIPE, text=True).stdout
    else:
        subprocess.run(cmd, check=check)
        return ''

def canonical_hash(el):
    return hashlib.sha256(etree.tostring(el, method='c14n')).hexdigest()

def parse_changesets_from_xml_bytes(xml_bytes, virtual_path):
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as e:
        raise RuntimeError(f'XML parse error in {virtual_path}: {e}')
    ns = root.nsmap.get(None)
    xp = "//lb:changeSet" if ns else "//changeSet"
    nsmap = {"lb": ns} if ns else None
    res = {}
    for cs in root.xpath(xp, namespaces=nsmap):
        key = (virtual_path, cs.get('id'), cs.get('author'))
        roc = (cs.get('runOnChange') or '').lower() == 'true'
        ralw = (cs.get('runAlways') or '').lower() == 'true'
        res[key] = {
            'runOnChange': roc,
            'runAlways': ralw,
            'hash': canonical_hash(cs)
        }
    return res

def git_show(ref, path):
    try:
        out = run(["git", "show", f"{ref}:{path}"], capture=True)
        return out.encode('utf-8')
    except subprocess.CalledProcessError:
        return None  # file does not exist at ref

def git_changed_files(base_ref, head_ref):
    out = run(["git", "diff", "--name-only", f"{base_ref}...{head_ref}"], capture=True)
    return [line.strip() for line in out.splitlines() if line.strip()]

def load_cfg(cfg_path):
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)
    lb = cfg.get('liquibase', {})
    if not lb:
        raise SystemExit('Config error: missing "liquibase" section')
    return lb

def load_exceptions(exceptions_file):
    if not exceptions_file or not Path(exceptions_file).exists():
        return []
    data = yaml.safe_load(Path(exceptions_file).read_text()) or {}
    return data.get('exceptions', [])

def is_in_paths(path, base_paths):
    path = Path(path)
    return any(str(path).startswith(p.rstrip('/') + '/') or str(path) == p for p in base_paths)

def matches_extensions(path, exts):
    return any(path.endswith(ext) for ext in exts)

def matches_any_pattern(name, patterns):
    return any(fnmatch(name, p) for p in patterns)

def whitelisted(ex_list, file_path, cs_id, author):
    for ex in ex_list:
        f_ok = fnmatch(file_path, ex.get('file',''))
        i_ok = fnmatch(cs_id or '', ex.get('id',''))
        a_ok = fnmatch(author or '', ex.get('author',''))
        if f_ok and i_ok and a_ok:
            return True
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True)
    ap.add_argument('--head', required=False, default='HEAD')
    ap.add_argument('--baseName', required=False, help='Base branch name (overrides env GITHUB_BASE_REF)')
    args = ap.parse_args()

    cfg = load_cfg(args.config)
    base_patterns = cfg.get('baseBranchPatterns', ['main'])
    exceptions_file = cfg.get('exceptionsFile')
    exceptions = load_exceptions(exceptions_file)

    # Determine base branch name
    base_name = args.baseName or os.environ.get('GITHUB_BASE_REF') or 'main'

    # Skip if base branch doesn't match configured patterns
    if not matches_any_pattern(base_name, base_patterns):
        print(f"ℹ️  Base-Branch '{base_name}' matcht keine Patterns {base_patterns} → Check wird übersprungen")
        sys.exit(0)

    base_ref = f"origin/{base_name}"
    head_ref = args.head

    # Get changed files between base and head
    try:
        changed = git_changed_files(base_ref, head_ref)
    except subprocess.CalledProcessError as e:
        print(f"Fehler bei git diff: {e}", file=sys.stderr)
        sys.exit(2)

    # Filter by config paths + extensions
    base_paths = cfg.get('changelogPaths', [])
    exts = cfg.get('fileExtensions', ['.xml'])
    target_files = [f for f in changed if is_in_paths(f, base_paths) and matches_extensions(f, exts)]

    if not target_files:
        print('ℹ️  Keine relevanten geänderten Dateien gefunden – nichts zu prüfen')
        print('✅ Liquibase governance check passed')
        return

    violations = []

    for file_path in target_files:
        old_bytes = git_show(base_ref, file_path)
        new_bytes = git_show(head_ref, file_path)

        if new_bytes is None:
            # deleted file or binary; skip
            continue

        new_sets = parse_changesets_from_xml_bytes(new_bytes, file_path)
        old_sets = parse_changesets_from_xml_bytes(old_bytes, file_path) if old_bytes else {}

        for key, now in new_sets.items():
            old = old_sets.get(key)
            if old and old['hash'] != now['hash']:
                if now['runOnChange'] or now['runAlways']:
                    continue
                if whitelisted(exceptions, file_path, key[1], key[2]):
                    continue
                violations.append({
                    'file': file_path,
                    'id': key[1],
                    'author': key[2]
                })

    if violations:
        print('❌ Liquibase Governance Violations (nur geänderte Dateien):', file=sys.stderr)
        for v in violations:
            print(f" - {v['file']} :: id={v['id']} author={v['author']} (modified without runOnChange/runAlways)", file=sys.stderr)
        sys.exit(1)

    print('✅ Liquibase governance check passed')

if __name__ == '__main__':
    main()
