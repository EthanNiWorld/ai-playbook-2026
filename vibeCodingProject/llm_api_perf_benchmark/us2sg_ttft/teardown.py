#!/usr/bin/env python3
"""Release the throwaway Virginia ECS and its temp network resources.

Order: instance (Force) -> security group -> vSwitch -> VPC, with waits.
Reads resource ids from state.json written by provision.py.
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def _arg(name, default):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


REGION = _arg("--region", "us-east-1")
STATE = os.path.join(HERE, f"state_{REGION}.json")
PROFILE = "ecsdeploy"


def cli(*args, ok_missing=False):
    r = subprocess.run(["aliyun", *args, "--profile", PROFILE],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        if ok_missing and "NotFound" in (r.stdout + r.stderr):
            return None
        raise RuntimeError(f"cli failed: {' '.join(args[:3])}\n{r.stderr[:400]}")
    return json.loads(r.stdout) if r.stdout.strip() else {}


def main():
    with open(STATE) as f:
        s = json.load(f)

    iid = s["instance_id"]
    # --RegionId is required to hit the right regional endpoint (profile
    # default is cn-beijing; without it the delete silently no-ops)
    cli("ecs", "DeleteInstance", "--InstanceId", iid, "--Force", "true",
        "--RegionId", REGION, ok_missing=True)
    print("delete instance issued:", iid)
    for _ in range(40):
        d = cli("ecs", "DescribeInstances", "--RegionId", REGION,
                "--InstanceIds", json.dumps([iid]))
        if not d["Instances"]["Instance"]:
            print("instance released")
            break
        time.sleep(5)
    else:
        raise RuntimeError("instance still present after wait")

    # ENI cleanup after instance release is async; DependencyViolation needs
    # patient retries, and exhaustion must fail loudly (never silent no-op)
    def delete_with_retry(desc, *args):
        for _ in range(30):
            try:
                cli(*args, ok_missing=True)
                print(desc, "deleted")
                return
            except RuntimeError:
                time.sleep(10)
        raise RuntimeError(f"{desc} NOT deleted after retries")

    delete_with_retry("sg", "ecs", "DeleteSecurityGroup", "--RegionId", REGION,
                      "--SecurityGroupId", s["sg_id"])
    delete_with_retry("vswitch", "vpc", "DeleteVSwitch", "--RegionId", REGION,
                      "--VSwitchId", s["vsw_id"])
    delete_with_retry("vpc", "vpc", "DeleteVpc", "--RegionId", REGION,
                      "--VpcId", s["vpc_id"])
    print("TEARDOWN_OK")


if __name__ == "__main__":
    main()