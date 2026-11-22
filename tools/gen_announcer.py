#!/usr/bin/env python3
"""Render announcer lines with the ElevenLabs text-to-speech API, once per line.

Reads audio/announcer/todo.csv (written by build.py: every line that still has no recording) and saves each
line as audio/announcer/<ID>.mp3. Lines that already have a file are skipped, so re-running only fills gaps
and never re-spends characters. Run `python3 build.py` afterwards to put the new files in the game.

The API key is read from the ELEVENLABS_API_KEY environment variable. It is never stored in the repo.

  python3 tools/gen_announcer.py --list-voices            # pick a voice_id from your account
  python3 tools/gen_announcer.py --voice <voice_id> --dry-run   # show what would be rendered + character count
  python3 tools/gen_announcer.py --voice <voice_id>             # render everything in todo.csv
  python3 tools/gen_announcer.py --voice <voice_id> --only rank-,sack_  # just lines whose ID starts with rank- or sack_
"""
import argparse, csv, json, os, sys, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANN_DIR = os.path.join(ROOT, 'audio', 'announcer')
API = 'https://api.elevenlabs.io/v1'


def request(path, key, body=None, accept='application/json'):
    req = urllib.request.Request(API + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={'xi-api-key': key, 'Content-Type': 'application/json', 'Accept': accept},
                                 method='GET' if body is None else 'POST')
    return urllib.request.urlopen(req, timeout=60)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--voice', help='ElevenLabs voice_id to use')
    ap.add_argument('--model', default='eleven_multilingual_v2', help='model_id (default: eleven_multilingual_v2)')
    ap.add_argument('--only', default='', help='only lines whose ID starts with one of these comma-separated prefixes')
    ap.add_argument('--list-voices', action='store_true', help='list the voices on your account and exit')
    ap.add_argument('--dry-run', action='store_true', help='print what would be rendered without calling the API')
    # delivery: calm broadcast-booth read by default (high stability, no style exaggeration). Lower stability / raise style for more energy.
    ap.add_argument('--stability', type=float, default=0.7)
    ap.add_argument('--similarity', type=float, default=0.75)
    ap.add_argument('--style', type=float, default=0.0)
    ap.add_argument('--speed', type=float, default=1.0, help='speaking rate, 0.7-1.2 (1.0 = normal; lower = slower)')
    ap.add_argument('--boost', action='store_true', help='turn on speaker boost (punchier, louder presence)')
    ap.add_argument('--out', default=ANN_DIR, help='folder to save into (default: audio/announcer); use another folder for test renders')
    ap.add_argument('--force', action='store_true', help='re-render even if the file already exists (from announcer_lines.json, not todo.csv)')
    a = ap.parse_args()

    key = os.environ.get('ELEVENLABS_API_KEY', '').strip()
    if not key and not a.dry_run:
        sys.exit('Set ELEVENLABS_API_KEY first (export ELEVENLABS_API_KEY=...) - it is read from the environment only.')

    if a.list_voices:
        voices = json.load(request('/voices', key)).get('voices', [])
        for v in sorted(voices, key=lambda v: (v.get('category') or '', v.get('name') or '')):
            labels = ', '.join(f'{k}: {x}' for k, x in (v.get('labels') or {}).items())
            print(f"{v['voice_id']}  {v.get('name', ''):<24} {v.get('category', ''):<12} {labels}")
        return

    prefixes = tuple(x.strip() for x in a.only.split(',')) if a.only else ('',)
    if a.force:   # every matching line straight from announcer_lines.json
        lines = {k: v for k, v in json.load(open(os.path.join(ROOT, 'announcer_lines.json'))).items() if not k.startswith('_')}
        rows = [{'filename': k + '.mp3', 'text': v} for k, v in lines.items() if (k + '.mp3').startswith(prefixes)]
    else:
        todo_path = os.path.join(ANN_DIR, 'todo.csv')
        if not os.path.exists(todo_path):
            sys.exit('No audio/announcer/todo.csv - run python3 build.py first.')
        rows = [r for r in csv.DictReader(open(todo_path)) if r['filename'].startswith(prefixes)]
        rows = [r for r in rows if not os.path.exists(os.path.join(a.out, r['filename']))]
    chars = sum(len(r['text']) for r in rows)
    print(f'{len(rows)} lines to render, {chars} characters')
    if a.dry_run or not rows:
        for r in rows: print(f"  {r['filename']}: {r['text']}")
        return
    if not a.voice:
        sys.exit('Pass --voice <voice_id> (see --list-voices).')

    body = lambda text: {'text': text, 'model_id': a.model,
                         'voice_settings': {'stability': a.stability, 'similarity_boost': a.similarity,
                                            'style': a.style, 'use_speaker_boost': a.boost, 'speed': a.speed}}
    done = 0
    for r in rows:
        os.makedirs(a.out, exist_ok=True)
        out = os.path.join(a.out, r['filename'])
        for attempt in range(4):
            try:
                audio = request(f"/text-to-speech/{a.voice}?output_format=mp3_44100_128", key, body(r['text']), 'audio/mpeg').read()
                open(out, 'wb').write(audio)
                done += 1
                print(f"  saved {r['filename']} ({len(audio) // 1024} KB)")
                break
            except urllib.error.HTTPError as e:
                msg = e.read().decode(errors='replace')[:300]
                if e.code == 429 and attempt < 3:      # rate limited: back off and retry
                    time.sleep(2 * (attempt + 1)); continue
                sys.exit(f"  {r['filename']}: HTTP {e.code} {msg}\nStopped after {done} files; re-run to continue.")
        time.sleep(0.3)
    print(f'Rendered {done} lines. Now run: python3 build.py')


if __name__ == '__main__':
    main()
