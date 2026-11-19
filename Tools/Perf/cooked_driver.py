"""Drive a packaged (cooked) FoA build from outside the process: a cooked game has no Python.
  python Tools/Perf/cooked_driver.py --build P:/FoA-Builds/<dir> --plan smoke|l1|l2 [--presets 0,1,2,3]
         [--res 1920x1080] [--sample 4] [--tag x]

How: the build's FoA.exe opens a window (off-screen by default, --onscreen to watch it), input goes in with
PostMessage (keys and typed text), so the game never needs focus. Development builds: console commands are typed
into the game's console (backtick), state is read back with `getall <Class> <Prop>` from the game's log (-abslog), and
each (moment, preset) gets a native CSV profile (`csvprofile start/stop`) and a HighResShot, like perf_driver.py.
Shipping builds have no console and no log: plan smoke only (keys and window captures, process alive).

Safety: runs only builds under P:/FoA-Builds (never P:/FoA, whose .uasset files the shared editor must be able to
save), kills only the PID it started, plays in the QA slot (GI_FoA.SetProofProgressContext('FoA_QA_Play')), and
puts the packaged game's own save folders back afterwards.
Output: P:/FoA/Saved/Perf/cooked/<stamp>_<plan>_<tag>/ (game.log, csv/, shots/, driver.json)."""
import argparse
import ctypes
import ctypes.wintypes as wt
import json
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

user32 = ctypes.WinDLL('user32', use_last_error=True)
gdi32 = ctypes.WinDLL('gdi32')
WM_KEYDOWN, WM_KEYUP, WM_CHAR = 0x100, 0x101, 0x102
VK = dict(ENTER=0x0D, SPACE=0x20, ESC=0x1B, TILDE=0xC0, E=0x45, **{f'F{i}': 0x6F + i for i in range(1, 13)})
# The console key: this machine's fr-CA layout makes backtick a dead key, so UE never sees Tilde. Perf Development
# builds from Tools/Perf/pack.sh add F7 (DefaultInput.ini in the pack mirror only).
CONSOLE_KEY = 'F7'
BUILDS = Path('P:/FoA-Builds')
# Steps of the playtest skip measured in the 11-18 04:12 run: 14 = the fight's intro (beat 8; Space skips it, the fight then runs),
# 17 = the T10 door portal, 18 = the 'Day one.' card before the dream room, 22 = the drive to Queen Market.
DWELL = {14: ('SPACE', 3), 18: (None, 3), 22: ('HOLD_W', 3)}  # 22: free steering since 11-18, so hold the throttle
STEPS = 24  # smoke: F6 presses (Level 1 is about 20 steps to the end of the fight, then Level 2)


def windows_of(pid):
    found = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid and user32.IsWindowVisible(hwnd):
            cls = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(hwnd, cls, 64)
            if cls.value == 'UnrealWindow':
                found.append(hwnd)
        return True
    user32.EnumWindows(cb, 0)
    return found


class Game:
    def __init__(self, build, out, res, onscreen, exec_extra='', extra_args=(), firstboot=False):
        # Windows/FoA.exe is only a bootstrap that starts the real binary as a child (whose window we need): run the
        # real one, FoA.exe (Development) or FoA-Win64-Shipping.exe, directly.
        exe = next((Path(build) / 'Windows/FoA/Binaries/Win64').glob('FoA*.exe'))
        assert BUILDS in exe.parents, f'only builds under {BUILDS} are run, not {exe}'
        self.out, self.log, self.t0 = out, out / 'game.log', time.time()
        self.shipping = 'Shipping' in exe.name
        self.saves = [Path(build) / 'Windows/FoA/Saved', Path.home() / 'AppData/Local/FoA/Saved']
        self.backup = {}
        for d in self.saves:  # the packaged game's own saves and settings: restored in close()
            if d.exists():
                self.backup[d] = out / ('saved_backup_' + str(len(self.backup)))
                shutil.copytree(d, self.backup[d], ignore=shutil.ignore_patterns('Logs', 'Profiling', 'Screenshots', 'Crashes'))
        self.firstboot = firstboot
        if firstboot:  # a new player's first launch: no settings yet, so the game must run its own auto-detect
            for d in self.saves:  # engine settings, and the game's own Settings.sav (it holds bGraphicsDetected)
                for f in [*d.glob('Config/**/GameUserSettings.ini'), *d.glob('SaveGames/Settings.sav')]:
                    f.unlink()
        rx, ry = res.split('x')
        args = [str(exe), '-windowed', f'-ResX={rx}', f'-ResY={ry}', '-nosound', f'-abslog={self.log}',
                '-WinX=0' if onscreen else '-WinX=-3840', '-WinY=0', '-ExecCmds=t.MaxFPS 0, r.VSync 0, '
                'r.GPUCsvStatsEnabled 1, r.ProfileGPU.ShowUI 0' + exec_extra, *extra_args]
        self.proc = subprocess.Popen(args)
        (out / 'pid.txt').write_text(str(self.proc.pid))
        self.hwnd, self.pos, self.rows, self.console = None, 0, [], False

    # ---- input --------------------------------------------------------------------------------------------------
    def window(self, timeout=90):
        end = time.time() + timeout
        while time.time() < end and self.proc.poll() is None:
            w = windows_of(self.proc.pid)
            if w:
                self.hwnd = w[0]
                return True
            time.sleep(0.5)
        return False

    def key_down(self, name):
        vk = VK[name] if name in VK else ord(name.upper())
        user32.PostMessageW(self.hwnd, WM_KEYDOWN, vk, 1 | (user32.MapVirtualKeyW(vk, 0) << 16))

    def key_up(self, name):
        vk = VK[name] if name in VK else ord(name.upper())
        user32.PostMessageW(self.hwnd, WM_KEYUP, vk, 1 | (user32.MapVirtualKeyW(vk, 0) << 16) | (0xC0 << 24))

    def key(self, name, hold=0.06):
        vk = VK[name] if name in VK else (name if isinstance(name, int) else ord(name.upper()))
        scan = user32.MapVirtualKeyW(vk, 0)
        user32.PostMessageW(self.hwnd, WM_KEYDOWN, vk, 1 | (scan << 16))
        time.sleep(hold)
        user32.PostMessageW(self.hwnd, WM_KEYUP, vk, 1 | (scan << 16) | (0xC0 << 24))
        time.sleep(0.05)

    def open_console(self):
        """The full console (console key twice) stays open after Enter and takes every key, so menus can't steal
        typed commands. Open it while no menu listens for keys (the splash, or gameplay)."""
        if not self.console:
            self.key(CONSOLE_KEY)
            time.sleep(0.2)
            self.key(CONSOLE_KEY)
            time.sleep(0.3)
            self.console = True

    def ensure_console(self, timeout=30):
        """Open the full console and prove it: a probe command must answer twice in a row (the second proves the
        console stayed open). Keys sent before the map has loaded are dropped, so wait for that first."""
        end = time.time() + timeout
        while time.time() < end and not any('LoadMap' in l or 'Bringing up level' in l for l in self.lines()):
            time.sleep(0.5)
        while time.time() < end and self.alive():
            self.console = False
            self.open_console()
            if self.probe() and self.probe():
                self.note('console_open')
                return True
            time.sleep(1.0)
        self.note('miss', what='console')
        return False

    def lines(self):
        return self.log.read_text(encoding='utf-8', errors='replace').splitlines() if self.log.exists() else []

    def probe(self):
        self.read()
        for ch in 'getall GameUserSettings bUseVSync':
            user32.PostMessageW(self.hwnd, WM_CHAR, ord(ch), 1)
        self.key('ENTER')
        end = time.time() + 2.0
        while time.time() < end:
            time.sleep(0.3)
            if any('bUseVSync =' in l for l in self.read()):
                return True
        return False

    def close_console(self):
        if self.console:
            self.key(CONSOLE_KEY)
            time.sleep(0.2)
            self.console = False

    def cmd(self, text):
        self.open_console()
        for ch in text:
            user32.PostMessageW(self.hwnd, WM_CHAR, ord(ch), 1)
        time.sleep(0.05)
        self.key('ENTER')
        time.sleep(0.25)
        self.note('cmd', text=text)

    # ---- state from the log ---------------------------------------------------------------------------------------
    def read(self):
        if not self.log.exists():
            return []
        with open(self.log, encoding='utf-8', errors='replace') as fh:
            fh.seek(self.pos)
            data = fh.read()
            self.pos = fh.tell()
        return data.splitlines()

    def get(self, cls, prop, wait=3.0):
        """getall <cls> <prop> -> {short object name: value text}"""
        self.read()
        self.cmd(f'getall {cls} {prop}')
        end, found = time.time() + wait, {}
        pat = re.compile(r'\d+\) \S+ \S*?\.?([A-Za-z0-9_]+)\.' + re.escape(prop) + r' = (.*)$')
        while time.time() < end and not found:
            time.sleep(0.3)
            for line in self.read():
                m = pat.search(line)
                if m and 'Default__' not in line:
                    found[m.group(1)] = m.group(2).strip()
        return found

    def one(self, cls, prop):
        v = self.get(cls, prop)
        return next(iter(v.items()), (None, None))

    def wait_prop(self, cls, prop, ok, timeout, what):
        end = time.time() + timeout
        while time.time() < end and self.alive():
            name, value = self.one(cls, prop)
            if value is not None and ok(value):
                return name
            time.sleep(0.7)
        self.note('miss', what=what)
        return None

    def alive(self):
        return self.proc.poll() is None

    def note(self, kind, **kw):
        self.rows.append(dict(t=round(time.time() - self.t0, 2), kind=kind, **kw))
        (self.out / 'driver.json').write_text(json.dumps(self.rows, indent=1))

    def wait_ready(self, timeout=240):
        """Slow boots outlast fixed sleeps (11-18 14:06: with the shared editor importing, the map loaded 100 s after
        launch and every key before it was lost). Development: the bedroom's LoadMap line in the log. Shipping (no
        log): the first bright capture, i.e. the title (splash and black frames measure 0 to 1, the title 44 to 54)."""
        from PIL import Image, ImageStat
        end = time.time() + timeout
        while time.time() < end and self.alive():
            if self.shipping:
                if ImageStat.Stat(Image.open(self.capture('boot_poll')).convert('L')).mean[0] > 25:
                    break
            elif self.log.exists() and 'to LoadMap(/Game/FoA/Maps/L_Tutorial_Bedroom)' in self.log.read_text(errors='replace'):
                break
            time.sleep(2.0)
        self.note('ready', after=round(time.time() - self.t0, 1))
        time.sleep(3.0)

    # ---- measuring ------------------------------------------------------------------------------------------------
    def capture(self, name):
        """Window capture through DWM (works for Shipping, which has no HighResShot)."""
        r = wt.RECT()
        user32.GetClientRect(self.hwnd, ctypes.byref(r))
        w, h = r.right, r.bottom
        hdc = user32.GetDC(self.hwnd)
        mdc = gdi32.CreateCompatibleDC(hdc)
        bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
        gdi32.SelectObject(mdc, bmp)
        user32.PrintWindow(self.hwnd, mdc, 3)  # PW_CLIENTONLY | PW_RENDERFULLCONTENT
        buf = ctypes.create_string_buffer(w * h * 4)
        bmi = (ctypes.c_uint32 * 10)(40, w, -h, 1 | (32 << 16), 0, 0, 0, 0, 0, 0)
        gdi32.GetDIBits(mdc, bmp, 0, h, buf, bmi, 0)
        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(mdc)
        user32.ReleaseDC(self.hwnd, hdc)
        from PIL import Image
        path = self.out / 'shots' / f'{name}.png'
        Image.frombuffer('RGBA', (w, h), buf, 'raw', 'BGRA', 0, 1).convert('RGB').save(path)
        self.note('capture', name=name, path=str(path))
        return path

    def measure(self, moment, presets, sample, settle=1.5):
        for p in presets:
            self.cmd(f'scalability {p}')
            time.sleep(settle)
            self.cmd(f'HighResShot 1 filename={(self.out / "shots" / f"{moment}_q{p}.png").as_posix()}')
            time.sleep(0.6)
            self.cmd('csvprofile start')
            self.close_console()  # the open console is drawn every frame: keep it out of the sample
            t0 = time.time()
            time.sleep(sample)
            self.cmd('csvprofile stop')
            self.note('segment', moment=moment, preset=p, t0=t0, t1=time.time())
            time.sleep(0.8)

    def window_note(self, name, sample):
        time.sleep(0.8)
        t0 = time.time()
        time.sleep(sample)
        self.note('window', name=name, t0=t0, t1=time.time())

    def close(self):
        if self.alive():
            if self.hwnd:  # WM_CLOSE: a normal exit request, works without a console (Shipping)
                user32.PostMessageW(self.hwnd, 0x0010, 0, 0)
            try:
                self.proc.wait(20)
            except subprocess.TimeoutExpired:
                subprocess.run(['taskkill', '/T', '/F', '/PID', str(self.proc.pid)], capture_output=True)
        self.note('exit', code=self.proc.poll())
        if self.firstboot:  # keep what the first launch wrote (the proof), before the originals go back
            for k, d in enumerate(self.saves):
                for f in d.glob('Config/**/GameUserSettings.ini'):
                    dest = self.out / 'firstboot' / f'savedir{k}' / f.relative_to(d)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dest)
                    self.note('firstboot_settings', path=str(dest))
        for d in self.saves:  # put the packaged game's saves back exactly as they were
            if d in self.backup:
                for sub in ('SaveGames', 'Config'):
                    if (d / sub).exists():
                        shutil.rmtree(d / sub)
                    if (self.backup[d] / sub).exists():
                        shutil.copytree(self.backup[d] / sub, d / sub)
            elif d.exists():
                for sub in ('SaveGames', 'Config'):
                    shutil.rmtree(d / sub, ignore_errors=True)


# ---- plans -----------------------------------------------------------------------------------------------------------
def boot(g):
    """Real front end through its own handlers, as perf_driver.boot_front_end does."""
    gi = g.wait_prop('GI_FoA_C', 'SaveSlot', lambda v: True, 60, 'game instance')
    fe = g.wait_prop('BP_FoAFrontEnd_C', 'bInGameplay', lambda v: True, 30, 'front end')
    d, _ = g.one('BP_BeatDirector_C', 'BeatIndex')
    g.note('names', gi=gi, fe=fe, director=d)
    g.cmd(f'ke {gi} SetProofProgressContext FoA_QA_Play () ()')
    g.cmd(f'ke {gi} ResetProgress')
    _, slot = g.one('GI_FoA_C', 'SaveSlot')
    g.note('save_slot', slot=slot)
    assert slot and 'FoA_QA_Play' in slot, f'QA save slot did not take: {slot}'
    for fn in ('OnSplashFinished', 'OnTitleConfirmed', 'WakeUp'):
        g.cmd(f'ke {fe} {fn}')
        time.sleep(0.4)
    end = time.time() + 25
    while time.time() < end and g.alive():
        _, story = g.one('BP_FoAFrontEnd_C', 'Story')
        m = re.search(r'\.([A-Za-z0-9_]+)\'?"?$', story or '')
        if m and 'None' not in story:
            g.cmd(f'ke {m.group(1)} Finish')
        _, ingame = g.one('BP_FoAFrontEnd_C', 'bInGameplay')
        if ingame == 'True':
            break
        time.sleep(0.5)
    time.sleep(1.0)
    g.cmd(f'ke {d} SkipWakeUp')
    g.wait_prop('BP_BeatDirector_C', 'bWakeDone', lambda v: v == 'True', 20, 'wake done')
    time.sleep(1.0)
    g.cmd(f'ke {fe} ClosePhone')
    g.note('booted', beat=g.one('BP_BeatDirector_C', 'BeatIndex')[1])
    return gi, fe, d


def plan_l1(g, presets, sample):
    gi, fe, d = boot(g)
    time.sleep(3)
    g.measure('bedroom', presets, sample)
    g.cmd(f'ke {d} EnterBeat 8')
    if g.wait_prop('BP_FoAPlayer_C', 'bCinematic', lambda v: v == 'True', 10, 'battle intro'):
        time.sleep(1.6)
        g.cmd(f'ke {d} SkipWakeUp')
    if g.wait_prop('BP_Encounter_C', 'bActive', lambda v: v == 'True', 15, 'encounter active'):
        g.cmd('slomo 0.5')
        time.sleep(1.0)
        g.measure('battle', presets, sample)
        g.cmd('slomo 1')


def plan_l2(g, presets, sample):
    """threshold_proof's non-job route: T10 by EnterBeat, the native transition, then the fixtures to the city."""
    gi, fe, d = boot(g)
    p, _ = g.one('BP_FoAPlayer_C', 'bCinematic')
    g.cmd(f'ke {p} Equip Suit')
    g.cmd(f'ke {p} SetBootsWorn true')
    g.cmd(f'ke {d} EnterBeat 10')
    g.cmd(f'ke {p} K2_TeleportTo (X=240,Y=87.5,Z=92) (Pitch=0,Yaw=0,Roll=0)')
    th = g.wait_prop('BP_DreamThreshold_C', 'Phase', lambda v: True, 15, 'threshold spawned')
    end = time.time() + 20
    while th and time.time() < end and g.alive():  # T10 phone: close it, the threshold then starts by itself
        g.cmd(f'ke {fe} ClosePhone')
        _, ph = g.one('BP_DreamThreshold_C', 'Phase')
        if ph and ph.lstrip('-').isdigit() and int(ph) >= 1:
            break
        time.sleep(1.0)
    g.cmd('slomo 0.2')
    time.sleep(1.5)
    g.measure('door_portal', presets, min(sample, 3))
    g.cmd('slomo 3')
    g.wait_prop('BP_DreamThreshold_C', 'Phase', lambda v: v.isdigit() and int(v) >= 3, 40, 'dream walk')
    g.cmd('slomo 1')
    time.sleep(2.5)
    g.measure('dream_room', presets, sample)
    g.cmd('set BP_DreamThreshold_C RouteBeat 2')
    g.cmd(f'ke {th} HidePath')
    g.cmd(f'ke {p} K2_TeleportTo (X=20000,Y=-79660,Z=92) (Pitch=0,Yaw=0,Roll=0)')
    g.cmd(f'ke {th} BeginFall')
    g.cmd('slomo 3')
    jn = g.wait_prop('BP_L2Journey_C', 'Phase', lambda v: True, 60, 'city arrival')
    g.wait_prop('BP_DreamThreshold_C', 'Phase', lambda v: v.isdigit() and int(v) >= 6, 30, 'phase 6')
    g.cmd('slomo 1')
    if jn:
        time.sleep(1.5)
        g.cmd(f'ke {jn} Confirm')
        time.sleep(0.3)
        g.cmd(f'ke {jn} Confirm')
        time.sleep(3.0)
        g.measure('city_drive', presets, sample)
        g.cmd(f'ke {th} BeginEnding')
        time.sleep(2.0)
        g.measure('ending', presets, sample)


def plan_smoke(g, presets, sample):
    """Shipping: no console or log. Keys through the front end, window captures, F6 playtest steps, still alive."""
    g.wait_ready()
    for i, k in enumerate(['ENTER', 'ENTER']):  # title Wake up, then the story card (what landed after the title)
        g.capture(f'smoke_{i}_before_{k}')
        g.key(k)
        time.sleep(4.0)
    g.key('SPACE', hold=1.5)  # hold Space skips the wake film
    time.sleep(6.0)
    g.capture('smoke_t0_phone')
    g.key('E')  # the T0 phone's confirm (E/Enter); F6 does not skip an open phone
    for i in range(STEPS):  # F6: one playtest step each (Levels 1 and 2); E closes phones that rise on the way
        time.sleep(5.0)
        if not g.alive():
            break
        g.capture(f'smoke_f6_{i:02d}')
        g.key('F6')
        if i % 3 == 2:
            time.sleep(1.0)
            g.key('E')
    g.note('smoke_alive', alive=g.alive())


def plan_steps(g, presets, sample):
    """Development builds without a usable console (this game's widgets keep every key, so the console key never
    reaches the viewport): the preset and `csvprofile start` come from -ExecCmds at launch, the game is booted with keys
    and advanced with its own playtest step (F9 diagnostics open, F6 = next step in Levels 1 and 2). After each step:
    a capture with the diagnostics showing the beat, then the overlay is closed for a `sample`-second window that is
    cut out of the run's single CSV afterwards (split_csv)."""
    g.wait_ready()
    for k in ['ENTER'] * 5:  # title Wake up and the story cards (the old 8 x 3 s from launch: 5 landed after the title)
        g.key(k)
        time.sleep(3.0)
    g.key('SPACE', hold=1.5)  # skip the wake film
    time.sleep(5.0)
    g.key('E')  # T0 phone
    time.sleep(3.0)
    g.capture('step_00_T1')
    g.window_note('step_00_T1', sample)
    g.key('F9')
    for i in range(1, STEPS + 1):
        if not g.alive():
            break
        g.key('F6')
        time.sleep(1.2)
        g.key('E')  # phones that rise on the way (E is also interact: harmless here)
        time.sleep(0.6)
        g.capture(f'step_{i:02d}')
        g.key('F9')  # overlay off while measuring
        g.window_note(f'step_{i:02d}', sample)
        if i in DWELL:  # stay at the heavy moments the next F6 would skip
            key, n = DWELL[i]
            held = key and key.startswith('HOLD_')
            if held:  # e.g. HOLD_W: throttle down for the whole dwell (the drive is player-steered now)
                g.key_down(key[5:])
            elif key:
                g.key(key, hold=1.5)
                time.sleep(1.5)
            for j in range(n):
                g.window_note(f'step_{i:02d}_dwell{j}', sample)
            g.capture(f'step_{i:02d}_dwell_end')
            if held:
                g.key_up(key[5:])
        g.key('F9')


def plan_fkeys(g, presets, sample):
    """Shipping: the playtest keys must do nothing (ui lane gates them on GetBuildConfiguration() != "Shipping").
    Boot to T1, then capture before and after each F-key and write fkeys_sheet.png (top row before, bottom after)."""
    g.wait_ready()
    for k in ['ENTER'] * 2:
        g.key(k)
        time.sleep(4.0)
    g.key('SPACE', hold=1.5)
    time.sleep(6.0)
    g.key('E')
    time.sleep(8.0)  # T1 "Take a few steps."
    g.capture('fkeys_t1')
    shots = []
    for k in ('F6', 'F7', 'F8', 'F9', 'F10'):
        before = g.capture(f'fkey_{k}_before')
        g.key(k)
        time.sleep(2.5)
        shots.append((k, before, g.capture(f'fkey_{k}_after')))
        g.note('fkey', key=k, alive=g.alive())
    from PIL import Image, ImageDraw
    w, h = 480, 270
    sheet = Image.new('RGB', (w * len(shots), h * 2))
    for i, (k, b, a) in enumerate(shots):
        for row, p in enumerate((b, a)):
            im = Image.open(p).convert('RGB').resize((w, h))
            ImageDraw.Draw(im).text((4, 4), f'{k} {"before" if row == 0 else "after"}', fill=(255, 0, 0))
            sheet.paste(im, (i * w, row * h))
    sheet.save(g.out / 'fkeys_sheet.png')


def plan_stills(g, presets, sample):
    """Development build at the preset from --presets (stills for the submission, main 11-19): the title, the wake
    film, then every playtest step (F6) captured with the diagnostics panel closed (F9), after the view settles."""
    g.wait_ready()
    time.sleep(4.0)
    g.key('ENTER')  # past the press-any-key title to the menu
    time.sleep(3.0)
    g.capture('stills_00_title')
    for _ in range(4):  # Wake up and the story cards
        g.key('ENTER')
        time.sleep(3.0)
    time.sleep(4.0)
    g.capture('stills_01_wake')
    g.key('SPACE', hold=1.5)  # skip the rest of the wake film
    time.sleep(5.0)
    g.key('E')  # T0 phone
    time.sleep(3.0)
    g.capture('stills_02_T1')
    g.key('F9')  # diagnostics open: F6 steps only with it up
    for i in range(1, STEPS + 1):
        if not g.alive():
            break
        g.key('F6')
        time.sleep(1.2)
        g.key('E')
        time.sleep(2.0)
        if i in DWELL and DWELL[i][0] == 'SPACE':  # the battle intro: skip into the fight
            g.key('SPACE', hold=1.5)
            time.sleep(3.0)
        g.key('F9')  # panel off for the still
        time.sleep(1.2)
        g.capture(f'stills_{i + 2:02d}_step{i:02d}')
        g.key('F9')


PLANS = dict(l1=plan_l1, l2=plan_l2, smoke=plan_smoke, steps=plan_steps, fkeys=plan_fkeys, stills=plan_stills)


def log_epoch(line):
    """UTC timestamp prefix of a UE log line ([2026.11.18-09.10.03:123][frame]) as epoch seconds."""
    m = re.match(r'\[(\d{4}\.\d\d\.\d\d-\d\d\.\d\d\.\d\d:\d{3})\]', line)
    if not m:
        return None
    from datetime import timezone
    return datetime.strptime(m.group(1), '%Y.%m.%d-%H.%M.%S:%f').replace(tzinfo=timezone.utc).timestamp()


def split_csv(csv_path, log_path, windows):
    """Cut one whole-run CSV into the driver's wall-clock windows. Row i ends at capture start + sum of FrameTime;
    the capture starts when -ExecCmds ran `csvprofile start`, whose echo (or the preceding t.MaxFPS echo) is logged."""
    import statistics
    from perf_run import read_csv, pct, STATS
    start = None
    for line in Path(log_path).read_text(encoding='utf-8', errors='replace').splitlines():
        if line.endswith('t.MaxFPS = "0"'):  # the first -ExecCmds echo: csvprofile start runs in the same frame
            start = log_epoch(line)
            break
    assert start, 'capture start not found in the log'
    cols = read_csv(csv_path)
    ends, t = [], start
    for ms in cols['FrameTime']:
        t += ms / 1000
        ends.append(t)
    out = []
    for w in windows:
        idx = [i for i, e in enumerate(ends) if w['t0'] <= e <= w['t1']]
        stats = {}
        for name in STATS:
            v = [cols[name][i] for i in idx if name in cols and i < len(cols[name])]
            if v:
                stats[name] = dict(p50=round(statistics.median(v), 2), p95=round(pct(v, .95), 2), max=round(max(v), 1), n=len(v))
        gpu = {k[4:]: round(statistics.mean([v[i] for i in idx if i < len(v)]), 3)
               for k, v in cols.items() if k.startswith('GPU/') and idx}
        if idx:  # the game's own GPU work (all GPU/* passes incl. Unaccounted): immune to another process on the GPU
            own = [sum(v[i] for k, v in cols.items() if k.startswith('GPU/') and i < len(v)) for i in idx]
            stats['GPUOwn'] = dict(p50=round(statistics.median(own), 2), p95=round(pct(own, .95), 2))
        stats['gpu_top'] = dict(sorted(gpu.items(), key=lambda kv: -kv[1])[:12])
        hitches = [round(cols['FrameTime'][i]) for i in idx if cols['FrameTime'][i] > 33]
        out.append(dict(moment=w['name'], frames=len(idx), stats=stats, hitches=hitches))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--build', required=True)
    ap.add_argument('--plan', default='smoke')
    ap.add_argument('--presets', default='0,1,2,3')
    ap.add_argument('--sample', type=float, default=4)
    ap.add_argument('--res', default='1920x1080')
    ap.add_argument('--tag', default='run')
    ap.add_argument('--onscreen', action='store_true')
    ap.add_argument('--dwell', help='override DWELL as JSON, e.g. {"17": [null, 5]} (step: [key or null, extra windows])')
    ap.add_argument('--steps', type=int, help='override STEPS (number of F6 steps)')
    ap.add_argument('--exec', default='', help='extra -ExecCmds for the steps plan, comma-separated (e.g. r.DynamicRes.FrameTimeBudget 5)')
    ap.add_argument('--firstboot', action='store_true', help='launch with no GameUserSettings (a new player); keep what it writes')
    ap.add_argument('--logpso', action='store_true', help='record PSOs (-logPSO) into the build''s Saved/CollectedPSOs')
    a = ap.parse_args()
    global DWELL, STEPS
    if a.dwell:
        DWELL = {int(k): tuple(v) for k, v in json.loads(a.dwell).items()}
    if a.steps:
        STEPS = a.steps
    out = Path('P:/FoA/Saved/Perf/cooked') / f"{datetime.now():%m%d_%H%M%S}_{a.plan}_{a.tag}"
    (out / 'shots').mkdir(parents=True)
    preset = a.presets.split(',')[0]
    extra = {'steps': f', scalability {preset}, csvprofile start', 'stills': ''}.get(a.plan, '')
    if a.exec and a.plan == 'steps':
        extra += ', ' + a.exec
    g = Game(a.build, out, a.res, a.onscreen, extra, ['-logPSO'] if a.logpso else [], a.firstboot)
    try:
        assert g.window(), 'no game window'
        from perf_run import others_gpu  # the shared editor's GPU use inflates our timings (perf_run.others_gpu)
        g.note('others_gpu', at='start', pct=others_gpu({g.proc.pid}))
        if not g.shipping and a.plan in ('l1', 'l2'):
            assert g.ensure_console(), 'console did not open'  # during the splash, before the title listens
        PLANS[a.plan](g, [int(x) for x in a.presets.split(',')], a.sample)
        g.note('others_gpu', at='end', pct=others_gpu({g.proc.pid}))
        g.note('plan_done', alive=g.alive())
    except Exception as exc:  # report and still close the game and restore its saves
        g.note('error', error=repr(exc))
    finally:
        g.close()
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from perf_run import match_csvs, summarize_csv, table
    segs = [r for r in g.rows if r['kind'] == 'segment']
    csv_dir = Path(a.build) / 'Windows/FoA/Saved/Profiling/CSV'
    files = sorted(f for f in csv_dir.glob('*.csv') if f.stat().st_mtime >= g.t0 - 1) if csv_dir.exists() else []
    (out / 'csv').mkdir(exist_ok=True)
    rows = []
    wins = [r for r in g.rows if r['kind'] == 'window']
    if wins and files:  # steps plan: one CSV for the whole run, cut into the step windows
        whole = out / 'csv' / f'run_q{preset}.csv'
        shutil.move(str(files[-1]), whole)
        rows = [dict(r, preset=preset) for r in split_csv(whole, g.log, wins)]
        (out / 'steps.json').write_text(json.dumps(rows, indent=1))
    for seg, f in zip(segs, match_csvs(segs, files)):
        row = dict(seg)
        if f:
            dest = out / 'csv' / f"{seg['moment']}_q{seg['preset']}.csv"
            shutil.move(str(f), dest)
            row['stats'] = summarize_csv(dest)
        rows.append(row)
    md = f'# cooked {a.plan} {a.tag} ({out.name})\n\n{table(rows)}\n'
    (out / 'summary.md').write_text(md)
    print(md)
    print(json.dumps([r for r in g.rows if r['kind'] in ('miss', 'error', 'names', 'save_slot', 'booted', 'exit', 'plan_done')],
                     indent=1))
    print('out', out)


if __name__ == '__main__':
    main()
