#!/usr/bin/env python3
"""Provision a throwaway pay-as-you-go ECS in us-east-1 (Virginia) for US->SG TTFT test.

Uses aliyun CLI profile `ecsdeploy`. Creates VPC/vSwitch/SG/instance, waits until
Running + CloudAssistant online, writes resource ids to state.json (same dir).
Teardown via teardown.py. No SSH ingress needed (Cloud Assistant channel only).
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
ZONE = _arg("--zone", {"us-east-1": "us-east-1a"}.get(REGION, REGION + "a"))
STATE = os.path.join(HERE, f"state_{REGION}.json")
PROFILE = "ecsdeploy"
NAME = f"ttft-bench-{REGION}-tmp"


def cli(*args, parse=True):
    cmd = ["aliyun", *args, "--profile", PROFILE]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"cli failed: {' '.join(args[:3])}\n{r.stdout}\n{r.stderr}")
    return json.loads(r.stdout) if parse else r.stdout


def load_state():
    if os.path.exists(STATE):
        with open(STATE) as f:
            return json.load(f)
    return {}


def save_state(s):
    with open(STATE, "w") as f:
        json.dump(s, f, indent=2)


def main():
    s = load_state()

    # stale-state guard: if the recorded instance no longer exists (released
    # in a previous run), start fresh instead of waiting on ghosts
    if "instance_id" in s:
        d = cli("ecs", "DescribeInstances", "--RegionId", REGION,
                "--InstanceIds", json.dumps([s["instance_id"]]))
        if not d["Instances"]["Instance"]:
            print("stale state detected (instance released), resetting")
            s = {}
            save_state(s)

    # 1. VPC
    if "vpc_id" not in s:
        d = cli("vpc", "CreateVpc", "--RegionId", REGION,
                "--CidrBlock", "172.16.0.0/16", "--VpcName", NAME)
        s["vpc_id"] = d["VpcId"]
        save_state(s)
        print("vpc:", s["vpc_id"])
    for _ in range(30):
        d = cli("vpc", "DescribeVpcs", "--RegionId", REGION, "--VpcId", s["vpc_id"])
        vpcs = d.get("Vpcs", {}).get("Vpc", [])
        if vpcs and vpcs[0]["Status"] == "Available":
            break
        time.sleep(2)

    # 2. vSwitch
    if "vsw_id" not in s:
        d = cli("vpc", "CreateVSwitch", "--RegionId", REGION, "--ZoneId", ZONE,
                "--VpcId", s["vpc_id"], "--CidrBlock", "172.16.0.0/24",
                "--VSwitchName", NAME)
        s["vsw_id"] = d["VSwitchId"]
        save_state(s)
        print("vswitch:", s["vsw_id"])
    time.sleep(3)

    # 3. Security group (egress only; Cloud Assistant needs no ingress)
    if "sg_id" not in s:
        d = cli("ecs", "CreateSecurityGroup", "--RegionId", REGION,
                "--VpcId", s["vpc_id"], "--SecurityGroupName", NAME)
        s["sg_id"] = d["SecurityGroupId"]
        save_state(s)
        print("sg:", s["sg_id"])

    # 4. Image: plain Alibaba Cloud Linux 3 x64 (cloud assistant + python3 + curl)
    if "image_id" not in s:
        d = cli("ecs", "DescribeImages", "--RegionId", REGION,
                "--ImageOwnerAlias", "system", "--ImageName",
                "aliyun_3_x64_20G_alibase_*", "--PageSize", "10")
        imgs = d.get("Images", {}).get("Image", [])
        if not imgs:
            raise RuntimeError("no plain aliyun3 image found")
        imgs.sort(key=lambda i: i["CreationTime"], reverse=True)
        s["image_id"] = imgs[0]["ImageId"]
        save_state(s)
        print("image:", s["image_id"])

    # 5. Instance
    if "instance_id" not in s:
        d = cli("ecs", "RunInstances", "--RegionId", REGION, "--ZoneId", ZONE,
                "--ImageId", s["image_id"], "--InstanceType", "ecs.e-c1m1.large",
                "--SecurityGroupId", s["sg_id"], "--VSwitchId", s["vsw_id"],
                "--InstanceName", NAME, "--InstanceChargeType", "PostPaid",
                "--InternetChargeType", "PayByTraffic",
                "--InternetMaxBandwidthOut", "100",
                "--SystemDisk.Category", "cloud_essd",
                "--SystemDisk.Size", "40",
                "--SystemDisk.PerformanceLevel", "PL0",
                "--Amount", "1")
        s["instance_id"] = d["InstanceIdSets"]["InstanceIdSet"][0]
        save_state(s)
        print("instance:", s["instance_id"])

    # 6. Wait Running + public IP
    for _ in range(60):
        d = cli("ecs", "DescribeInstances", "--RegionId", REGION,
                "--InstanceIds", json.dumps([s["instance_id"]]))
        ins = d["Instances"]["Instance"]
        if ins and ins[0]["Status"] == "Running":
            ips = ins[0].get("PublicIpAddress", {}).get("IpAddress", [])
            if ips:
                s["public_ip"] = ips[0]
                save_state(s)
                print("running, public ip:", s["public_ip"])
                break
        time.sleep(5)
    else:
        raise RuntimeError("instance not Running in time")

    # 7. Wait Cloud Assistant online
    for _ in range(40):
        d = cli("ecs", "DescribeCloudAssistantStatus", "--RegionId", REGION,
                "--InstanceId.1", s["instance_id"])
        sts = d.get("InstanceCloudAssistantStatusSet", {}).get("InstanceCloudAssistantStatus", [])
        if sts and sts[0].get("CloudAssistantStatus") == "true":
            print("cloud assistant online")
            break
        time.sleep(5)
    else:
        raise RuntimeError("cloud assistant not online in time")

    print("PROVISION_OK", json.dumps(s))


if __name__ == "__main__":
    main()