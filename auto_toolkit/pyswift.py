"""
PySwift Toolkit - Python Automation Utilities
================================================
A collection of practical CLI tools for developers and power users.
Sell on Gumroad as a digital product ($4.99 - $9.99)

Commands:
  batch-rename     Rename files in batch with pattern
  csv2json         Convert CSV to JSON
  extract-emails   Extract email addresses from text/files
  qr-gen           Generate QR code images
  merge-csv        Merge multiple CSV files
  dedup-lines      Remove duplicate lines from files
"""
import argparse
import csv
import json
import os
import re
import sys

def main():
    parser = argparse.ArgumentParser(description='PySwift Toolkit')
    sub = parser.add_subparsers(dest='cmd')

    # batch-rename
    p = sub.add_parser('batch-rename')
    p.add_argument('--dir', required=True)
    p.add_argument('--pattern', default='file_{n}')
    p.add_argument('--ext')
    p.add_argument('--start', type=int, default=1)
    p.add_argument('--dry-run', action='store_true')

    # csv2json
    p = sub.add_parser('csv2json')
    p.add_argument('--input', required=True)
    p.add_argument('--output')
    p.add_argument('--pretty', action='store_true')

    # extract-emails
    p = sub.add_parser('extract-emails')
    p.add_argument('--input', required=True)
    p.add_argument('--output')
    p.add_argument('--unique', action='store_true')

    # qr-gen
    p = sub.add_parser('qr-gen')
    p.add_argument('--text', required=True)
    p.add_argument('--output', default='qr.png')
    p.add_argument('--size', type=int, default=10)

    # merge-csv
    p = sub.add_parser('merge-csv')
    p.add_argument('--dir', required=True)
    p.add_argument('--output', default='merged.csv')

    # dedup-lines
    p = sub.add_parser('dedup-lines')
    p.add_argument('--input', required=True)
    p.add_argument('--output')

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return

    handlers = {
        'batch-rename': cmd_batch_rename,
        'csv2json': cmd_csv2json,
        'extract-emails': cmd_extract_emails,
        'qr-gen': cmd_qr_gen,
        'merge-csv': cmd_merge_csv,
        'dedup-lines': cmd_dedup_lines,
    }
    handlers[args.cmd](args)


def cmd_batch_rename(args):
    files = sorted(os.listdir(args.dir))
    ext_filter = args.ext
    if ext_filter:
        files = [f for f in files if f.endswith(ext_filter)]

    renamed = 0
    for i, fname in enumerate(files):
        new_name = args.pattern.replace('{n}', str(args.start + i))
        if ext_filter:
            new_name += ext_filter
        else:
            _, old_ext = os.path.splitext(fname)
            new_name += old_ext

        old_path = os.path.join(args.dir, fname)
        new_path = os.path.join(args.dir, new_name)

        if args.dry_run:
            print(f"  {fname} → {new_name}")
        else:
            os.rename(old_path, new_path)
        renamed += 1

    verb = "Would rename" if args.dry_run else "Renamed"
    print(f"✅ {verb} {renamed} files")


def cmd_csv2json(args):
    with open(args.input, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    output = args.output or args.input.replace('.csv', '.json')
    indent = 2 if args.pretty else None
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(rows, f, indent=indent, ensure_ascii=False)

    print(f"✅ Converted {len(rows)} rows → {output}")


def cmd_extract_emails(args):
    with open(args.input, 'r', encoding='utf-8') as f:
        text = f.read()

    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)

    if args.unique:
        seen = set()
        unique = []
        for e in emails:
            if e.lower() not in seen:
                seen.add(e.lower())
                unique.append(e)
        emails = unique

    output = args.output or 'emails.txt'
    with open(output, 'w', encoding='utf-8') as f:
        f.write('\n'.join(emails))

    print(f"✅ Extracted {len(emails)} email(s) → {output}")


def cmd_qr_gen(args):
    try:
        import qrcode
    except ImportError:
        print("Need qrcode: pip install qrcode[pil]")
        return

    img = qrcode.make(args.text)
    img.save(args.output)
    print(f"✅ QR saved → {args.output}")


def cmd_merge_csv(args):
    files = [f for f in os.listdir(args.dir) if f.endswith('.csv')]
    if not files:
        print("No CSV files found")
        return

    all_rows = []
    header = None
    for fname in files:
        path = os.path.join(args.dir, fname)
        with open(path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            h = next(reader)
            if header is None:
                header = h
            all_rows.extend(reader)

    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(all_rows)

    print(f"✅ Merged {len(files)} files, {len(all_rows)} rows → {args.output}")


def cmd_dedup_lines(args):
    with open(args.input, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    seen = set()
    unique = []
    for line in lines:
        stripped = line.rstrip('\n\r')
        if stripped not in seen:
            seen.add(stripped)
            unique.append(line)

    output = args.output or args.input
    with open(output, 'w', encoding='utf-8') as f:
        f.writelines(unique)

    removed = len(lines) - len(unique)
    print(f"✅ Removed {removed} duplicate(s), {len(unique)} lines → {output}")


if __name__ == '__main__':
    main()
