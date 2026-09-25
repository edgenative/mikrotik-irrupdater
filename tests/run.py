#!/usr/bin/env python3
# End-to-end tests for bin/mikrotik-irrupdater.py against a fake RouterOS API.
# No dependencies, no router needed:  python3 tests/run.py
#
# The fake API keeps its "router" in a JSON file so the updater (which runs as a
# subprocess, like cron would run it) and the test can both see it. It honours
# place-before and can be told to fail a specific add, which is enough to cover
# every safety check the updater makes.

import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAIN = "as1-sfmix-import-ipv4"

FAKE_API = '''
import json, os
STATE = os.environ["ROS_STATE"]
class _Resource:
    def _load(self):
        return json.load(open(STATE))
    def _save(self, d):
        json.dump(d, open(STATE, "w"))
    def get(self, chain):
        return [r for r in self._load()["rules"] if r["chain"] == chain]
    def add(self, rule, chain, disabled, **kw):
        if os.environ.get("ROS_FAIL_ADD") and os.environ["ROS_FAIL_ADD"] in rule:
            raise RuntimeError("simulated add failure")
        d = self._load()
        d["next"] += 1
        new = {"id": "*%X" % d["next"], "chain": chain, "rule": rule}
        before = kw.get("place-before")
        if before:
            idx = next(i for i, r in enumerate(d["rules"]) if r["id"] == before)
            d["rules"].insert(idx, new)
        else:
            d["rules"].append(new)
        self._save(d)
    def remove(self, id):
        d = self._load()
        d["rules"] = [r for r in d["rules"] if r["id"] != id]
        self._save(d)
class _Api:
    def get_resource(self, path):
        return _Resource()
class RouterOsApiPool:
    def __init__(self, *args, **kwargs):
        pass
    def get_api(self):
        return _Api()
'''


class Harness:
    def __init__(self):
        self.dir = tempfile.mkdtemp(prefix="mikrotik-irrupdater-test.")
        os.makedirs(os.path.join(self.dir, "filters"))
        os.makedirs(os.path.join(self.dir, "config"))
        with open(os.path.join(self.dir, "config", "routers.conf"), "w") as f:
            f.write("[API]\nusername=test\npassword=test\n")
        with open(os.path.join(self.dir, "routeros_api.py"), "w") as f:
            f.write(FAKE_API)
        # Point the updater at the temp tree instead of /usr/share/mikrotik-irrupdater
        src = open(os.path.join(ROOT, "bin", "mikrotik-irrupdater.py")).read()
        src = src.replace('path = "/usr/share/mikrotik-irrupdater"', 'path = %r' % self.dir)
        self.script = os.path.join(self.dir, "updater.py")
        open(self.script, "w").write(src)
        self.state = os.path.join(self.dir, "state.json")
        self.filter_file = os.path.join(self.dir, "filters", CHAIN + ".txt")
        self.baseline = os.path.join(self.dir, "filters", "last-pushed", CHAIN + ".txt")

    def cleanup(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write_filter(self, rules, chain=CHAIN):
        with open(self.filter_file, "w") as f:
            for r in rules:
                f.write("{'chain': '%s', 'rule': '%s'}\n" % (chain, r))

    def set_router(self, rules):
        json.dump({"next": 100, "rules": [{"id": "*%d" % i, "chain": CHAIN, "rule": r}
                                          for i, r in enumerate(rules, 1)]}, open(self.state, "w"))

    def router_rules(self):
        return [r["rule"] for r in json.load(open(self.state))["rules"]]

    def run(self, **env_extra):
        env = dict(os.environ, ROS_STATE=self.state, PYTHONPATH=self.dir)
        env.pop("IRRUPDATER_FORCE", None)
        env.pop("ROS_FAIL_ADD", None)
        env.update(env_extra)
        p = subprocess.run([sys.executable, self.script, CHAIN, self.filter_file, "router-under-test"],
                           capture_output=True, text=True, env=env)
        return p.returncode, (p.stdout + p.stderr)

    def baseline_text(self):
        return open(self.baseline).read() if os.path.isfile(self.baseline) else None


def rule(i):
    return "if (dst==10.0.%d.0/24) { jump sfmix-import }" % i


def main():
    h = Harness()
    results = []

    def check(name, ok, detail=""):
        results.append((name, ok, detail))

    try:
        # An empty file must be refused before the router is even contacted
        h.write_filter([]); h.set_router([rule(1)])
        rc, out = h.run()
        check("empty file refused", rc == 1 and "REFUSED" in out, out)

        open(h.filter_file, "w").write("this is not a rule\n")
        rc, out = h.run()
        check("malformed line refused", rc == 1 and "not a valid rule" in out, out)

        h.write_filter([rule(1)], chain="some-other-chain")
        rc, out = h.run()
        check("rules for another chain refused", rc == 1 and "expected" in out, out)

        # Up to date: nothing pushed, baseline seeded
        h.write_filter([rule(1)]); h.set_router([rule(1)])
        rc, out = h.run()
        check("match seeds baseline", rc == 0 and h.baseline_text() is not None, out)

        # Growth: new rules must land BEFORE the terminal reject, and be verified
        h.write_filter([rule(i) for i in range(1, 21)] + ["reject"]); h.set_router([rule(1), "reject"])
        rc, out = h.run()
        rr = h.router_rules()
        check("new rules placed before reject and verified",
              rc == 0 and rr[-1] == "reject" and len(rr) == 21 and "Verified" in out, out)

        # Shrink of more than 80% against the last pushed copy
        h.write_filter([rule(1), rule(2), "reject"])
        rc, out = h.run()
        check("shrink >80% refused", rc == 1 and "refusing" in out, out)

        # Every prefix rule gone (only the reject left)
        h.write_filter(["reject"])
        rc, out = h.run()
        check("losing all prefix rules refused", rc == 1 and "lost all" in out, out)

        # IRRUPDATER_FORCE=1 lets an expected shrink through, still verified
        h.write_filter([rule(1), rule(2), "reject"])
        rc, out = h.run(IRRUPDATER_FORCE="1")
        check("FORCE pushes the shrink and verifies", rc == 0 and h.router_rules() == [rule(1), rule(2), "reject"], out)

        # A failed add must not lead to removals, and must not touch the baseline
        before = h.baseline_text()
        h.write_filter([rule(5), rule(6), "reject"])
        rc, out = h.run(ROS_FAIL_ADD="10.0.6.0")
        rr = h.router_rules()
        check("add failure keeps old rules and baseline",
              rc == 1 and rule(1) in rr and rule(2) in rr and h.baseline_text() == before, out)
    finally:
        h.cleanup()

    failed = 0
    for name, ok, detail in results:
        print(("PASS  " if ok else "FAIL  ") + name)
        if not ok:
            failed += 1
            for line in detail.strip().splitlines()[-6:]:
                print("      " + line)
    print("%d passed, %d failed" % (len(results) - failed, failed))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
