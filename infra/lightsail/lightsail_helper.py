#!/usr/bin/env python3
"""
Lightsail Helper Script
Automates common Lightsail operations from your local machine.

Usage:
    python lightsail_helper.py list              # List all instances
    python lightsail_helper.py create <name>     # Create new instance
    python lightsail_helper.py ssh <name>        # SSH into instance
    python lightsail_helper.py setup <name>      # Run setup script on instance
    python lightsail_helper.py status <name>     # Check instance status
    python lightsail_helper.py key               # Download SSH key
"""

import subprocess
import json
import sys
import os
from pathlib import Path


def run_aws(cmd: list) -> dict | list | str:
    """Run AWS CLI command and return parsed JSON output."""
    try:
        result = subprocess.run(
            ["aws", "lightsail"] + cmd + ["--output", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except subprocess.CalledProcessError as e:
        print(f"AWS Error: {e.stderr}")
        return {}
    except json.JSONDecodeError:
        return result.stdout.strip()


def get_key_path() -> Path:
    """Get path to SSH key file."""
    home = Path.home()
    return home / "lightsail-key.pem"


def download_key():
    """Download Lightsail default SSH key."""
    print("Downloading Lightsail SSH key...")
    result = run_aws(["download-default-key-pair"])

    if not result:
        print("Failed to download key")
        return None

    key_path = get_key_path()
    key_content = result.get("privateKeyBase64", "")

    with open(key_path, "w", newline="\n") as f:
        f.write(key_content)

    # Set permissions (Unix only)
    if os.name != "nt":
        os.chmod(key_path, 0o600)

    print(f"Key saved to: {key_path}")
    return key_path


def list_instances():
    """List all Lightsail instances."""
    print("\n=== Lightsail Instances ===\n")
    result = run_aws(["get-instances"])

    instances = result.get("instances", [])
    if not instances:
        print("No instances found")
        return

    print(f"{'Name':<25} {'State':<12} {'IP':<16} {'Bundle':<12} {'OS'}")
    print("-" * 80)

    for inst in instances:
        name = inst.get("name", "")
        state = inst.get("state", {}).get("name", "")
        ip = inst.get("publicIpAddress", "N/A")
        bundle = inst.get("bundleId", "")
        blueprint = inst.get("blueprintId", "")
        print(f"{name:<25} {state:<12} {ip:<16} {bundle:<12} {blueprint}")


def get_instance(name: str) -> dict:
    """Get instance details by name."""
    result = run_aws(["get-instance", "--instance-name", name])
    return result.get("instance", {})


def create_instance(name: str, bundle: str = "small_3_0", region: str = "us-east-1a"):
    """Create a new Lightsail instance."""
    print(f"Creating instance: {name}")
    print(f"  Bundle: {bundle}")
    print(f"  Region: {region}")

    result = run_aws([
        "create-instances",
        "--instance-names", name,
        "--availability-zone", region,
        "--bundle-id", bundle,
        "--blueprint-id", "ubuntu_22_04"
    ])

    if result:
        print(f"Instance creation started!")
        print("Use 'python lightsail_helper.py status {name}' to check progress")
    return result


def ssh_command(name: str) -> str:
    """Get SSH command for instance."""
    inst = get_instance(name)
    if not inst:
        print(f"Instance '{name}' not found")
        return ""

    ip = inst.get("publicIpAddress")
    if not ip:
        print(f"Instance '{name}' has no public IP (may be stopped)")
        return ""

    key_path = get_key_path()
    if not key_path.exists():
        print("SSH key not found. Downloading...")
        download_key()

    return f'ssh -o StrictHostKeyChecking=no -i "{key_path}" ubuntu@{ip}'


def ssh_into(name: str):
    """SSH into an instance."""
    cmd = ssh_command(name)
    if cmd:
        print(f"Connecting to {name}...")
        os.system(cmd)


def run_setup(name: str):
    """Run setup script on instance."""
    inst = get_instance(name)
    if not inst:
        print(f"Instance '{name}' not found")
        return

    ip = inst.get("publicIpAddress")
    key_path = get_key_path()

    # Upload setup script
    script_path = Path(__file__).parent / "setup_instance.sh"
    if not script_path.exists():
        print(f"Setup script not found: {script_path}")
        return

    print("Uploading setup script...")
    subprocess.run([
        "scp", "-o", "StrictHostKeyChecking=no",
        "-i", str(key_path),
        str(script_path),
        f"ubuntu@{ip}:~/setup_instance.sh"
    ])

    print("Running setup script...")
    subprocess.run([
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-i", str(key_path),
        f"ubuntu@{ip}",
        "chmod +x ~/setup_instance.sh && ~/setup_instance.sh"
    ])


def show_status(name: str):
    """Show detailed instance status."""
    inst = get_instance(name)
    if not inst:
        print(f"Instance '{name}' not found")
        return

    print(f"\n=== Instance: {name} ===\n")
    print(f"State:     {inst.get('state', {}).get('name', 'unknown')}")
    print(f"IP:        {inst.get('publicIpAddress', 'N/A')}")
    print(f"Bundle:    {inst.get('bundleId', '')}")
    print(f"Blueprint: {inst.get('blueprintId', '')}")
    print(f"Region:    {inst.get('location', {}).get('availabilityZone', '')}")
    print(f"Created:   {inst.get('createdAt', '')}")

    # Hardware
    hw = inst.get("hardware", {})
    print(f"\nHardware:")
    print(f"  CPU:     {hw.get('cpuCount', 'N/A')} vCPUs")
    print(f"  RAM:     {hw.get('ramSizeInGb', 'N/A')} GB")
    print(f"  Disk:    {sum(d.get('sizeInGb', 0) for d in hw.get('disks', []))} GB")

    # SSH command
    if inst.get("publicIpAddress"):
        print(f"\nSSH Command:")
        print(f"  {ssh_command(name)}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()

    if cmd == "list":
        list_instances()

    elif cmd == "key":
        download_key()

    elif cmd == "create":
        if len(sys.argv) < 3:
            print("Usage: python lightsail_helper.py create <name> [bundle]")
            print("Bundles: nano_3_0, micro_3_0, small_3_0, medium_3_0, large_3_0")
            return
        name = sys.argv[2]
        bundle = sys.argv[3] if len(sys.argv) > 3 else "small_3_0"
        create_instance(name, bundle)

    elif cmd == "ssh":
        if len(sys.argv) < 3:
            print("Usage: python lightsail_helper.py ssh <name>")
            return
        ssh_into(sys.argv[2])

    elif cmd == "setup":
        if len(sys.argv) < 3:
            print("Usage: python lightsail_helper.py setup <name>")
            return
        run_setup(sys.argv[2])

    elif cmd == "status":
        if len(sys.argv) < 3:
            print("Usage: python lightsail_helper.py status <name>")
            return
        show_status(sys.argv[2])

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
