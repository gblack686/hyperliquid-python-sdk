"""
Docker Deployment Verification Script
Tests all components running in Docker containers
"""

import os
import time
import subprocess
import requests
from datetime import datetime

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text:^60}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def check_status(service_name, condition=True, message=""):
    if condition:
        print(f"{GREEN}[OK]{RESET} {service_name} - {message}")
        return True
    else:
        print(f"{RED}[FAIL]{RESET} {service_name} - {message}")
        return False

def run_command(command):
    """Run a shell command and return output"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout.strip(), result.returncode == 0
    except Exception as e:
        return str(e), False

def check_docker():
    """Check if Docker is running"""
    output, success = run_command("docker --version")
    return check_status("Docker", success, output if success else "Docker not found")

def check_containers():
    """Check if all containers are running"""
    containers = [
        "hl-indicators",
        "hl-trigger-analyzer",
        "hl-trigger-streamer", 
        "hl-paper-trader"
    ]
    
    all_running = True
    for container in containers:
        output, success = run_command(f'docker ps --filter name={container} --format "{{{{.Status}}}}"')
        
        if success and output and "Up" in output:
            check_status(f"Container: {container}", True, output)
        else:
            check_status(f"Container: {container}", False, "Not running")
            all_running = False
    
    return all_running

def check_api_health():
    """Check if the trigger analyzer API is healthy"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        healthy = response.status_code == 200
        return check_status("API Health", healthy, 
                           f"Status code: {response.status_code}")
    except Exception as e:
        return check_status("API Health", False, f"Cannot connect: {e}")

def check_logs():
    """Check recent logs for errors"""
    containers = [
        "hl-indicators",
        "hl-trigger-analyzer",
        "hl-trigger-streamer",
        "hl-paper-trader"
    ]
    
    print(f"\n{YELLOW}Recent Container Logs:{RESET}")
    for container in containers:
        output, success = run_command(f"docker logs {container} --tail 5 2>&1")
        if success and output:
            # Check for common error patterns
            has_error = any(word in output.lower() for word in ['error', 'exception', 'traceback'])
            
            if has_error:
                print(f"\n{RED}{container}:{RESET}")
                print(f"  {RED}Errors detected in logs{RESET}")
            else:
                print(f"\n{GREEN}{container}:{RESET}")
                print(f"  {GREEN}No recent errors{RESET}")

def check_network():
    """Check if the Docker network exists"""
    output, success = run_command('docker network ls --filter name=hyperliquid-net --format "{{.Name}}"')
    return check_status("Docker Network", 
                       success and "hyperliquid-net" in output,
                       "hyperliquid-net exists" if success else "Network not found")

def check_images():
    """Check if all images are built"""
    images = [
        "hyperliquid-trading-dashboard-indicators",
        "hyperliquid-trading-dashboard-trigger-analyzer",
        "hyperliquid-trading-dashboard-trigger-streamer",
        "hyperliquid-trading-dashboard-paper-trader"
    ]
    
    all_built = True
    for image in images:
        output, success = run_command(f'docker images {image} --format "{{{{.Repository}}}}:{{{{.Tag}}}}"')
        
        if success and output:
            check_status(f"Image: {image}", True, "Built")
        else:
            check_status(f"Image: {image}", False, "Not built")
            all_built = False
    
    return all_built

def check_resources():
    """Check Docker resource usage"""
    print(f"\n{YELLOW}Resource Usage:{RESET}")
    output, success = run_command('docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"')
    
    if success and output:
        lines = output.split('\n')
        for line in lines:
            if any(container in line for container in ["hl-indicators", "hl-trigger", "hl-paper"]):
                print(f"  {line}")

def main():
    print_header("DOCKER DEPLOYMENT VERIFICATION")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all checks
    checks = [
        ("Docker Installation", check_docker),
        ("Docker Network", check_network),
        ("Docker Images", check_images),
        ("Running Containers", check_containers),
        ("API Health Check", check_api_health),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n{YELLOW}Checking {name}...{RESET}")
        result = check_func()
        results.append(result)
        time.sleep(0.5)
    
    # Check logs
    check_logs()
    
    # Check resources
    check_resources()
    
    # Summary
    print_header("VERIFICATION SUMMARY")
    
    passed = sum(1 for r in results if r)
    total = len(results)
    
    if passed == total:
        print(f"{GREEN}[SUCCESS] All {total} checks passed!{RESET}")
        print(f"\n{GREEN}Docker deployment is fully operational.{RESET}")
    else:
        print(f"{RED}[WARNING] {passed}/{total} checks passed.{RESET}")
        print(f"\n{YELLOW}Some components may need attention.{RESET}")
        print(f"\n{YELLOW}Troubleshooting steps:{RESET}")
        print("1. Check logs: docker-compose logs")
        print("2. Restart services: docker-compose restart")
        print("3. Rebuild if needed: docker-compose build --no-cache")
    
    print(f"\n{BLUE}Use 'docker-run.bat status' for quick status check{RESET}")
    print(f"{BLUE}Use 'docker-run.bat logs' to view detailed logs{RESET}")

if __name__ == "__main__":
    main()