#!/usr/bin/env python3
"""候选翻页 + 漏字(issue #5) + 跟随全局每页候选数(issue #4) 的隔离 e2e。
断言两条链路: ProcessKeyEvent 返回值(按键是否被吞掉) 与插件日志里的
'commit candidate index=N'(数字选词落到了第几个候选)。
"""
import os, re, sys, time
import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

PS = int(sys.argv[1])
LOG = os.environ["WETYPE_PAGETEST_LOG"]
KEY = {"a": 97, "i": 105, "h": 104, "n": 110, "o": 111, "1": 49, "0": 48,
       "eq": 61, "minus": 45, "esc": 0xFF1B, "down": 0xFF54}

DBusGMainLoop(set_as_default=True)
bus = dbus.SessionBus()
CTL = dbus.Interface(bus.get_object("org.fcitx.Fcitx5", "/controller"),
                     "org.fcitx.Fcitx.Controller1")
IM = dbus.Interface(bus.get_object("org.fcitx.Fcitx5", "/org/freedesktop/portal/inputmethod"),
                    "org.fcitx.Fcitx.InputMethod1")
for _ in range(20):
    try:
        CTL.CurrentInputMethod()
        break
    except Exception:
        time.sleep(0.5)
else:
    print("FAIL: fcitx5 dbus 未就绪")
    sys.exit(1)

loop = GLib.MainLoop()
commits = []
bus.add_signal_receiver(lambda *a, **k: commits.append(str(a[0]) if a else ""),
                        dbus_interface="org.fcitx.Fcitx.InputContext1",
                        signal_name="CommitString")
CTL.SetCurrentIM("wetype-im")
time.sleep(0.5)
path, _ = IM.CreateInputContext([("program", "wetype-pagetest"),
                                 ("capability", dbus.String(str(dbus.UInt64(1 | (1 << 39)))))])
ic = dbus.Interface(bus.get_object("org.fcitx.Fcitx5", path),
                    "org.fcitx.Fcitx.InputContext1")
ic.FocusIn()
time.sleep(0.5)


def pump(seconds):
    end = time.time() + seconds
    while time.time() < end:
        loop.get_context().iteration(False)
        time.sleep(0.02)


def press(name):
    ok = ic.ProcessKeyEvent(dbus.UInt32(KEY[name]), dbus.UInt32(0), dbus.UInt32(0),
                            dbus.Boolean(False),
                            dbus.UInt32(int(time.time() * 1000) & 0xFFFFFFFF))
    pump(0.15)
    return bool(ok)


def indexes():
    with open(LOG, errors="ignore") as f:
        return [int(m) for m in re.findall(r"commit candidate index=(\d+)", f.read())]


def candidate_count():
    with open(LOG, errors="ignore") as f:
        m = re.findall(r"parsed candidates=(\d+)", f.read())
    return int(m[-1]) if m else 0


def fresh():
    press("esc")
    commits.clear()
    for ch in "nihao":
        press(ch)
    for _ in range(40):
        pump(0.25)
        if candidate_count() >= 2 * PS + 1:
            break
    return candidate_count()


results = []


def check(label, cond, detail=""):
    results.append((label, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + label + ("  " + detail if detail else ""), flush=True)


n = fresh()
check("engine returned enough candidates (>=2*%d+1)" % PS, n >= 2 * PS + 1, "count=%d" % n)

# 1) 未翻页时按数字 1 -> 第一个候选
before = len(indexes())
press("1")
pump(0.8)
got = indexes()
check("page 1 digit-1 commits index 0", len(got) > before and got[-1] == 0,
      "index=%s" % (got[-1] if got else None))

# 2) issue #5: 第一页按 '-' 无法后退, 但按键必须被吞掉且不产生上屏
fresh()
leak_before = len(commits)
consumed = press("minus")
pump(0.8)
check("issue#5 '-' on first page is consumed", consumed, "consumed=%s" % consumed)
check("issue#5 '-' leaks nothing into the document", len(commits) == leak_before,
      "commits=%s" % commits[leak_before:])

# 3) issue #4: 一次 '=' 前进 PS 个候选
fresh()
before = len(indexes())
press("eq")
press("1")
pump(0.8)
got = indexes()
check("one '=' then digit-1 commits index %d" % PS, len(got) > before and got[-1] == PS,
      "index=%s" % (got[-1] if got else None))

# 4) 两次 '=' 前进 2*PS
fresh()
before = len(indexes())
press("eq")
press("eq")
press("1")
pump(0.8)
got = indexes()
check("two '=' then digit-1 commits index %d" % (2 * PS),
      len(got) > before and got[-1] == 2 * PS, "index=%s" % (got[-1] if got else None))

# 5) 末尾页反复 '=' / '-' 不越界、不漏字, 回到首页后数字 1 仍是 index 0
fresh()
tail = all(press("eq") for _ in range(30))
head = all(press("minus") for _ in range(30))
check("paging keys stay consumed at both boundaries", tail and head)
before = len(indexes())
press("1")
pump(0.8)
got = indexes()
check("after paging back, digit-1 commits index 0",
      len(got) > before and got[-1] == 0, "index=%s" % (got[-1] if got else None))

# 6) 每页 10 个时, '0' 选第 10 个
if PS >= 10:
    fresh()
    before = len(indexes())
    press("0")
    pump(0.8)
    got = indexes()
    check("digit-0 commits the 10th candidate (index 9)",
          len(got) > before and got[-1] == 9, "index=%s" % (got[-1] if got else None))

failed = [r for r in results if not r[1]]
print("SUMMARY page_size=%d total=%d failed=%d" % (PS, len(results), len(failed)), flush=True)
print("E2E_RESULT =", "FAIL" if failed else "PASS", flush=True)
sys.exit(1 if failed else 0)
